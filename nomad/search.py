#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

'''
This module provides an interface to elasticsearch. Other parts of NOMAD must not
interact with elasticsearch to maintain a clear coherent interface and allow for change.

Currently NOMAD uses one entry index and two distinct materials indices. The entries
index is based on two different mappings, once used by the old flask api (v0) and one
used by the new fastapi api (v1). The mappings are used at the same time and the documents
are merged. Write operations (index, publish, edit, lift embargo, delete) are common; defined
here in the module ``__init__.py``. Read operations are different and
should be used as per use-case directly from the ``v0`` and ``v1`` submodules.

Most common functions also take an ``update_materials`` keyword arg with allows to
update the v1 materials index according to the performed changes. TODO this is only
partially implemented.
'''

from typing import Union, List, Iterable, Any, cast, Dict, Generator
import json
import elasticsearch
from elasticsearch.exceptions import TransportError, RequestError
from elasticsearch_dsl import Q, A, Search
from elasticsearch_dsl.query import Query as EsQuery
from pydantic.error_wrappers import ErrorWrapper

from nomad import config, infrastructure, utils
from nomad import datamodel
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.app.v1 import models as api_models
from nomad.app.v1.models import (
    AggregationPagination, MetadataPagination, Pagination, PaginationResponse,
    QuantityAggregation, Query, MetadataRequired,
    MetadataResponse, Aggregation, StatisticsAggregation, StatisticsAggregationResponse,
    Value, AggregationBase, TermsAggregation, BucketAggregation, HistogramAggregation,
    DateHistogramAggregation, MinMaxAggregation, Bucket,
    MinMaxAggregationResponse, TermsAggregationResponse, HistogramAggregationResponse,
    DateHistogramAggregationResponse, AggregationResponse)
from nomad.metainfo.elasticsearch_extension import (
    index_entries, entry_type, entry_index, DocumentType,
    material_type, entry_type, material_entry_type,
    entry_index, Index, index_entries, DocumentType, SearchQuantity)


def update_by_query(
        update_script: str,
        query: Any = None,
        owner: str = None,
        user_id: str = None,
        index: str = None,
        refresh: bool = False,
        **kwargs):
    '''
    Uses the given painless script to update the entries by given query.

    In most cases, the elasticsearch entry index should not be updated field by field;
    you should run `index` instead and fully replace documents from mongodb and
    archive files.

    This method provides a faster direct method to update individual fields, e.g. to quickly
    update fields for editing operations.
    '''
    if query is None:
        query = {}
    es_query = _api_to_es_query(query)
    if owner is not None:
        es_query &= _owner_es_query(owner=owner, user_id=user_id)

    body = {
        'script': {
            'source': update_script,
            'lang': 'painless'
        },
        'query': es_query.to_dict()
    }

    body['script'].update(**kwargs)

    try:
        result = infrastructure.elastic_client.update_by_query(
            body=body, index=config.elastic.entries_index)
    except TransportError as e:
        utils.get_logger(__name__).error(
            'es update_by_query script error', exc_info=e,
            es_info=json.dumps(e.info, indent=2))
        raise SearchError(e)

    if refresh:
        _refresh()

    return result


def delete_by_query(
        query: dict,
        owner: str = None,
        user_id: str = None,
        update_materials: bool = False,
        refresh: bool = False):
    '''
    Deletes all entries that match the given query.
    '''
    if query is None:
        query = {}
    es_query = _api_to_es_query(query)
    es_query &= _owner_es_query(owner=owner, user_id=user_id)

    body = {
        'query': es_query.to_dict()
    }

    try:
        result = infrastructure.elastic_client.delete_by_query(
            body=body, index=config.elastic.entries_index)
    except TransportError as e:
        utils.get_logger(__name__).error(
            'es delete_by_query error', exc_info=e,
            es_info=json.dumps(e.info, indent=2))
        raise SearchError(e)

    if refresh:
        _refresh()

    if update_materials:
        # TODO update the matrials index at least for v1
        pass

    return result


def refresh():
    '''
    Refreshes the specified indices.
    '''

    try:
        infrastructure.elastic_client.indices.refresh(index=config.elastic.entries_index)
    except TransportError as e:
        utils.get_logger(__name__).error(
            'es delete_by_query error', exc_info=e,
            es_info=json.dumps(e.info, indent=2))
        raise SearchError(e)


_refresh = refresh


def index(
        entries: Union[EntryArchive, List[EntryArchive]],
        update_materials: bool = False,
        refresh: bool = True):
    '''
    Index the given entries based on their archive. Either creates or updates the underlying
    elasticsearch documents. If an underlying elasticsearch document already exists it
    will be fully replaced.
    '''
    if not isinstance(entries, list):
        entries = [entries]

    index_entries(entries=entries, update_materials=update_materials)

    if refresh:
        _refresh()


# TODO this depends on how we merge section metadata
def publish(entries: Iterable[EntryMetadata], index: str = None) -> int:
    '''
    Publishes the given entries based on their entry metadata. Sets publishes to true,
    and updates most user provided metadata with a partial update. Returns the number
    of failed updates.
    '''
    return update_metadata(
        entries, index=index, published=True, update_materials=True, refresh=True)


def update_metadata(
        entries: Iterable[EntryMetadata], index: str = None,
        update_materials: bool = False, refresh: bool = False,
        **kwargs) -> int:
    '''
    Update all given entries with their given metadata. Additionally apply kwargs.
    Returns the number of failed updates. This is doing a partial update on the underlying
    elasticsearch documents.
    '''

    def elastic_updates():
        for entry_metadata in entries:
            entry_archive = entry_metadata.m_parent
            if entry_archive is None:
                entry_archive = EntryArchive(metadata=entry_metadata)
            entry_doc = entry_type.create_index_doc(entry_archive)

            entry_doc.update(**kwargs)

            yield dict(
                doc=entry_doc,
                _id=entry_metadata.calc_id,
                _type=entry_index.doc_type.name,
                _index=entry_index.index_name,
                _op_type='update')

    updates = list(elastic_updates())
    _, failed = elasticsearch.helpers.bulk(
        infrastructure.elastic_client, updates, stats_only=True)

    if update_materials:
        # TODO update the matrials index at least for v1
        pass

    if refresh:
        _refresh()

    return failed


def delete_upload(upload_id: str, refresh: bool = False, **kwargs):
    '''
    Deletes the given upload.
    '''
    delete_by_query(query=dict(upload_id=upload_id), **kwargs)

    if refresh:
        _refresh()


def delete_entry(entry_id: str, index: str = None, refresh: bool = False, **kwargs):
    '''
    Deletes the given entry.
    '''
    delete_by_query(query=dict(calc_id=entry_id), **kwargs)

    if refresh:
        _refresh()


class SearchError(Exception): pass


class AuthenticationRequiredError(Exception): pass


_entry_metadata_defaults = {
    quantity.name: quantity.default
    for quantity in datamodel.EntryMetadata.m_def.quantities  # pylint: disable=not-an-iterable
    if quantity.default not in [None, [], False, 0]
}


def _es_to_entry_dict(hit, required: MetadataRequired = None) -> Dict[str, Any]:
    '''
    Elasticsearch entry metadata does not contain default values, if a metadata is not
    set. This will add default values to entry metadata in dict form obtained from
    elasticsearch.
    '''
    entry_dict = hit.to_dict()
    for key, value in _entry_metadata_defaults.items():
        if key not in entry_dict:
            if required is not None:
                if required.exclude and key in required.exclude:
                    continue
                if required.include and key not in required.include:
                    continue

            entry_dict[key] = value

    return entry_dict


def _api_to_es_query(query: api_models.Query) -> Q:
    '''
    Creates an ES query based on the API's query model. This needs to be a normalized
    query expression with explicit objects for logical, set, and comparison operators.
    Shorthand notations ala ``quantity:operator`` are not supported here; this
    needs to be resolved via the respective pydantic validator. There is also no
    validation of quantities and types.
    '''
    def quantity_to_es(name: str, value: api_models.Value) -> Q:
        # TODO depends on keyword or not, value might need normalization, etc.
        quantity = entry_type.quantities[name]
        return Q('match', **{quantity.search_field: value})

    def parameter_to_es(name: str, value: api_models.QueryParameterValue) -> Q:

        if isinstance(value, api_models.All):
            return Q('bool', must=[
                quantity_to_es(name, item)
                for item in value.op])

        if isinstance(value, api_models.Any_):
            return Q('bool', should=[
                quantity_to_es(name, item)
                for item in value.op])

        if isinstance(value, api_models.None_):
            return Q('bool', must_not=[
                quantity_to_es(name, item)
                for item in value.op])

        if isinstance(value, api_models.Range):
            quantity = entry_type.quantities[name]
            return Q('range', **{quantity.search_field: value.dict(
                exclude_unset=True,
            )})

        # list of values is treated as an "all" over the items
        if isinstance(value, list):
            return Q('bool', must=[
                quantity_to_es(name, item)
                for item in value])

        return quantity_to_es(name, cast(api_models.Value, value))

    def query_to_es(query: api_models.Query) -> Q:
        if isinstance(query, api_models.LogicalOperator):
            if isinstance(query, api_models.And):
                return Q('bool', must=[query_to_es(operand) for operand in query.op])

            if isinstance(query, api_models.Or):
                return Q('bool', should=[query_to_es(operand) for operand in query.op])

            if isinstance(query, api_models.Not):
                return Q('bool', must_not=query_to_es(query.op))

            raise NotImplementedError()

        if not isinstance(query, dict):
            raise NotImplementedError()

        # dictionary is like an "and" of all items in the dict
        if len(query) == 0:
            return Q()

        if len(query) == 1:
            key = next(iter(query))
            return parameter_to_es(key, query[key])

        return Q('bool', must=[
            parameter_to_es(name, value) for name, value in query.items()])

    return query_to_es(query)


def _owner_es_query(owner: str, user_id: str = None, doc_type: DocumentType = entry_type):
    def term_query(**kwargs):
        prefix = '' if doc_type == entry_type else 'entries.'
        return Q('term', **{
            (prefix + field): value for field, value in kwargs.items()})

    if owner == 'all':
        q = term_query(published=True)
        if user_id is not None:
            q = q | term_query(viewers__user_id=user_id)
    elif owner == 'public':
        q = term_query(published=True) & term_query(with_embargo=False)
    elif owner == 'visible':
        q = term_query(published=True) & term_query(with_embargo=False)
        if user_id is not None:
            q = q | term_query(viewers__user_id=user_id)
    elif owner == 'shared':
        if user_id is None:
            raise AuthenticationRequiredError('Authentication required for owner value shared.')

        q = term_query(viewers__user_id=user_id)
    elif owner == 'user':
        if user_id is None:
            raise AuthenticationRequiredError('Authentication required for owner value user.')

        q = term_query(main_author__user_id=user_id)
    elif owner == 'staging':
        if user_id is None:
            raise AuthenticationRequiredError('Authentication required for owner value user')
        q = term_query(published=False) & term_query(viewers__user_id=user_id)
    elif owner == 'admin':
        if user_id is None or not datamodel.User.get(user_id=user_id).is_admin:
            raise AuthenticationRequiredError('This can only be used by the admin user.')
        q = None
    elif owner is None:
        q = None
    else:
        raise KeyError('Unsupported owner value')

    if q is not None:
        return q
    return Q()


class QueryValidationError(Exception):
    def __init__(self, error, loc):
        self.errors = [ErrorWrapper(Exception(error), loc=loc)]


def validate_quantity(
        quantity_name: str, value: Value = None, doc_type: DocumentType = None,
        loc: List[str] = None) -> SearchQuantity:
    '''
    Validates the given quantity name and value against the given document type.

    Returns:
        A metainfo elasticsearch extension SearchQuantity object.

    Raises: QueryValidationError
    '''
    assert quantity_name is not None

    if doc_type == material_entry_type and not quantity_name.startswith('entries'):
        quantity_name = f'entries.{quantity_name}'

    if doc_type == material_type and quantity_name.startswith('entries'):
        doc_type = material_entry_type

    if doc_type is None:
        doc_type = entry_type

    quantity = doc_type.quantities.get(quantity_name)
    if quantity is None:
        raise QueryValidationError(
            f'{quantity_name} is not a {doc_type} quantity',
            loc=[quantity_name] if loc is None else loc)

    return quantity


def _create_es_must(queries: Dict[str, EsQuery]):
    # dictionary is like an "and" of all items in the dict
    if len(queries) == 0:
        return Q()

    if len(queries) == 1:
        return list(queries.values())[0]

    return Q('bool', must=list(queries.values()))


def validate_api_query(
        query: Query, doc_type: DocumentType, owner_query: EsQuery,
        prefix: str = None, results_dict: Dict[str, EsQuery] = None) -> EsQuery:
    '''
    Creates an ES query based on the API's query model. This needs to be a normalized
    query expression with explicit objects for logical, set, and comparison operators.
    Shorthand notations ala ``quantity:operator`` are not supported here; this
    needs to be resolved via the respective pydantic validator.

    However, this function performs validation of quantities and types and raises
    a QueryValidationError accordingly. This exception is populated with pydantic
    errors.

    Arguments:
        query: The api query object.
        doc_type:
            The elasticsearch metainfo extension document type that this query needs to
            be verified against.
        owner_query:
            A prebuild ES query that is added to nested entries query. Only for
            materials queries.
        prefix:
            An optional prefix that is added to all quantity names. Used for recursion.
        results_dict:
            If an empty dictionary is given and the query is a mapping, the top-level
            criteria from this mapping will be added as individual es queries. The
            keys will be the mapping keys and values the respective es queries. A logical
            and (or es "must") would result in the overall resulting es query.

    Returns:
        A elasticsearch dsl query object.

    Raises: QueryValidationError
    '''

    def match(name: str, value: Value) -> EsQuery:
        if name == 'optimade_filter':
            value = str(value)
            from nomad.app.optimade import filterparser
            try:
                return filterparser.parse_filter(value, without_prefix=True)

            except filterparser.FilterException as e:
                raise QueryValidationError(
                    f'Could not parse optimade filter: {e}',
                    loc=[name])

        # TODO non keyword quantities, quantities with value transformation, type checks
        quantity = validate_quantity(name, value, doc_type=doc_type)
        return Q('match', **{quantity.search_field: value})

    def validate_query(query: Query) -> EsQuery:
        return validate_api_query(
            query, doc_type=doc_type, owner_query=owner_query, prefix=prefix)

    def validate_criteria(name: str, value: Any):
        if prefix is not None:
            name = f'{prefix}.{name}'

        # handle prefix and nested queries
        for nested_key in doc_type.nested_object_keys:
            if len(name) < len(nested_key):
                break
            if not name.startswith(nested_key):
                continue
            if prefix is not None and prefix.startswith(nested_key):
                continue
            if nested_key == name and isinstance(value, api_models.Nested):
                continue

            value = api_models.Nested(query={name[len(nested_key) + 1:]: value})
            name = nested_key
            break

        if isinstance(value, api_models.All):
            return Q('bool', must=[match(name, item) for item in value.op])

        elif isinstance(value, api_models.Any_):
            return Q('bool', should=[match(name, item) for item in value.op])

        elif isinstance(value, api_models.None_):
            return Q('bool', must_not=[match(name, item) for item in value.op])

        elif isinstance(value, api_models.Range):
            quantity = validate_quantity(name, None, doc_type=doc_type)
            return Q('range', **{quantity.search_field: value.dict(
                exclude_unset=True,
            )})

        elif isinstance(value, (api_models.And, api_models.Or, api_models.Not)):
            return validate_query(value)

        elif isinstance(value, api_models.Nested):
            sub_doc_type = material_entry_type if name == 'entries' else doc_type

            sub_query = validate_api_query(
                value.query, doc_type=sub_doc_type, prefix=name, owner_query=owner_query)

            if name in doc_type.nested_object_keys:
                if name == 'entries':
                    sub_query &= owner_query
                return Q('nested', path=name, query=sub_query)
            else:
                return sub_query

        # list of values is treated as an "all" over the items
        elif isinstance(value, list):
            return Q('bool', must=[match(name, item) for item in value])

        elif isinstance(value, dict):
            assert False, (
                'Using dictionaries as criteria values directly is not supported. Use the '
                'Nested model.')

        else:
            return match(name, value)

    if isinstance(query, api_models.And):
        return Q('bool', must=[validate_query(operand) for operand in query.op])

    if isinstance(query, api_models.Or):
        return Q('bool', should=[validate_query(operand) for operand in query.op])

    if isinstance(query, api_models.Not):
        return Q('bool', must_not=validate_query(query.op))

    if isinstance(query, dict):
        # dictionary is like an "and" of all items in the dict
        if len(query) == 0:
            return Q()

        if len(query) == 1:
            name = next(iter(query))
            es_criteria_query = validate_criteria(name, query[name])
            if results_dict is not None:
                results_dict[name] = es_criteria_query
            return es_criteria_query

        es_criteria_queries = []
        for name, value in query.items():
            es_criteria_query = validate_criteria(name, value)
            es_criteria_queries.append(es_criteria_query)
            if results_dict is not None:
                results_dict[name] = es_criteria_query

        return Q('bool', must=es_criteria_queries)

    raise NotImplementedError()


def validate_pagination(pagination: Pagination, doc_type: DocumentType, loc: List[str] = None):
    order_quantity = None
    if pagination.order_by is not None:
        order_quantity = validate_quantity(
            pagination.order_by, doc_type=doc_type, loc=['pagination', 'order_by'])
        if not order_quantity.definition.is_scalar:
            raise QueryValidationError(
                'the order_by quantity must be a scalar',
                loc=(loc if loc else []) + ['pagination', 'order_by'])

    page_after_value = pagination.page_after_value
    if page_after_value is not None and \
            pagination.order_by is not None and \
            pagination.order_by != doc_type.id_field and \
            ':' not in page_after_value:

        pagination.page_after_value = '%s:' % page_after_value

    return order_quantity, page_after_value


def _api_to_es_aggregation(
        es_search: Search, name: str, agg: AggregationBase, doc_type: DocumentType,
        post_agg_queries: Dict[str, EsQuery]) -> A:
    '''
    Creates an ES aggregation based on the API's aggregation model.
    '''

    agg_name = f'agg:{name}'
    es_aggs = es_search.aggs

    if post_agg_queries:
        filter = post_agg_queries
        if isinstance(agg, QuantityAggregation) and agg.exclude_from_search:
            filter = {name: query for name, query in post_agg_queries.items() if name != agg.quantity}
        es_aggs = es_aggs.bucket(f'{agg_name}:filtered', A('filter', filter=_create_es_must(filter)))

    if isinstance(agg, StatisticsAggregation):
        for metric_name in agg.metrics:
            metrics = doc_type.metrics
            if metric_name not in metrics and doc_type == material_type:
                metrics = material_entry_type.metrics
            if metric_name not in metrics:
                raise QueryValidationError(
                    'metric must be the qualified name of a suitable search quantity',
                    loc=['statistic', 'metrics'])
            metric_aggregation, metric_quantity = metrics[metric_name]
            es_aggs.metric('statistics:%s' % metric_name, A(
                metric_aggregation,
                field=metric_quantity.qualified_field))

        return

    agg = cast(QuantityAggregation, agg)
    longest_nested_key = None
    quantity = validate_quantity(agg.quantity, doc_type=doc_type, loc=['aggregation', 'quantity'])
    for nested_key in doc_type.nested_object_keys:
        if agg.quantity.startswith(nested_key):
            es_aggs = es_aggs.bucket('nested_agg:%s' % name, 'nested', path=nested_key)
            longest_nested_key = nested_key

    es_agg = None

    if isinstance(agg, TermsAggregation):
        if not quantity.aggregateable:
            raise QueryValidationError(
                'The aggregation quantity cannot be used in a terms aggregation.',
                loc=['aggregation', name, 'terms', 'quantity'])

        if agg.pagination is not None:
            if agg.size is not None:
                raise QueryValidationError(
                    f'You cannot paginate and provide an extra size parameter.',
                    loc=['aggregations', name, 'terms', 'pagination'])

            order_quantity, page_after_value = validate_pagination(
                agg.pagination, doc_type=doc_type, loc=['aggregation'])

            # We are using elastic searchs 'composite aggregations' here. We do not really
            # compose aggregations, but only those pseudo composites allow us to use the
            # 'after' feature that allows to scan through all aggregation values.
            terms = A('terms', field=quantity.search_field, order=agg.pagination.order.value)

            if order_quantity is None:
                composite = {
                    'sources': {
                        name: terms
                    },
                    'size': agg.pagination.page_size
                }

            else:
                sort_terms = A(
                    'terms',
                    field=order_quantity.search_field,
                    order=agg.pagination.order.value)

                composite = {
                    'sources': [
                        {order_quantity.search_field: sort_terms},
                        {quantity.search_field: terms}
                    ],
                    'size': agg.pagination.page_size
                }

            if page_after_value is not None:
                if post_agg_queries:
                    raise QueryValidationError(
                        f'aggregation page_after_value cannot be used with exclude_from_search in the same request',
                        loc=['aggregations', name, 'terms', 'pagination', 'page_after_value'])

                if order_quantity is None:
                    composite['after'] = {name: page_after_value}
                else:
                    try:
                        order_value, quantity_value = page_after_value.split(':')
                        composite['after'] = {quantity.search_field: quantity_value, order_quantity.search_field: order_value}
                    except Exception:
                        raise QueryValidationError(
                            f'The pager_after_value has not the right format.',
                            loc=['aggregations', name, 'terms', 'pagination', 'page_after_value'])

            es_agg = es_aggs.bucket(agg_name, 'composite', **composite)

            # additional cardinality to get total
            es_aggs.metric('agg:%s:total' % name, 'cardinality', field=quantity.search_field)
        else:
            if agg.size is None:
                if quantity.default_aggregation_size is not None:
                    agg.size = quantity.default_aggregation_size

                elif quantity.values is not None:
                    agg.size = len(quantity.values)

                else:
                    agg.size = 10

            terms_kwargs = {}
            if agg.value_filter is not None:
                terms_kwargs['include'] = '.*%s.*' % agg.value_filter

            terms = A('terms', field=quantity.search_field, size=agg.size, **terms_kwargs)
            es_agg = es_aggs.bucket(agg_name, terms)

        if agg.entries is not None and agg.entries.size > 0:
            kwargs: Dict[str, Any] = {}
            if agg.entries.required is not None:
                if agg.entries.required.include is not None:
                    kwargs.update(_source=dict(includes=agg.entries.required.include))
                else:
                    kwargs.update(_source=dict(excludes=agg.entries.required.exclude))

            es_agg.metric('entries', A('top_hits', size=agg.entries.size, **kwargs))

    elif isinstance(agg, DateHistogramAggregation):
        if not quantity.annotation.mapping['type'] in ['date']:
            raise QueryValidationError(
                f'The quantity {quantity} cannot be used in a date histogram aggregation',
                loc=['aggregations', name, 'histogram', 'quantity'])

        es_agg = es_aggs.bucket(agg_name, A(
            'date_histogram', field=quantity.search_field, interval=agg.interval,
            format='yyyy-MM-dd'))

    elif isinstance(agg, HistogramAggregation):
        if not quantity.annotation.mapping['type'] in ['integer', 'float', 'double', 'long']:
            raise QueryValidationError(
                f'The quantity {quantity} cannot be used in a histogram aggregation',
                loc=['aggregations', name, 'histogram', 'quantity'])

        es_agg = es_aggs.bucket(agg_name, A(
            'histogram', field=quantity.search_field, interval=agg.interval))

    elif isinstance(agg, MinMaxAggregation):
        if not quantity.annotation.mapping['type'] in ['integer', 'float', 'double', 'long', 'date']:
            raise QueryValidationError(
                f'The quantity {quantity} cannot be used in a mix-max aggregation',
                loc=['aggregations', name, 'min_max', 'quantity'])

        es_aggs.metric(agg_name + ':min', A('min', field=quantity.search_field))
        es_aggs.metric(agg_name + ':max', A('max', field=quantity.search_field))

    else:
        raise NotImplementedError()

    if isinstance(agg, BucketAggregation):
        for metric_name in agg.metrics:
            metrics = doc_type.metrics
            if longest_nested_key == 'entries':
                metrics = material_entry_type.metrics
            if metric_name not in metrics:
                raise QueryValidationError(
                    'metric must be the qualified name of a suitable search quantity',
                    loc=['statistic', 'metrics'])
            metric_aggregation, metric_quantity = metrics[metric_name]
            es_agg.metric('metric:%s' % metric_name, A(
                metric_aggregation,
                field=metric_quantity.qualified_field))


def _es_to_api_aggregation(
        es_response, name: str, agg: AggregationBase, doc_type: DocumentType):
    '''
    Creates a AggregationResponse from elasticsearch response on a request executed with
    the given aggregation.
    '''
    es_aggs = es_response.aggs

    filtered_agg_name = f'agg:{name}:filtered'
    if filtered_agg_name in es_response.aggs:
        es_aggs = es_aggs[f'agg:{name}:filtered']

    aggregation_dict = agg.dict(by_alias=True)

    if isinstance(agg, StatisticsAggregation):
        metrics = {}
        for metric in agg.metrics:  # type: ignore
            metrics[metric] = es_aggs[f'statistics:{metric}'].value

        return AggregationResponse(
            statistics=StatisticsAggregationResponse(data=metrics, **aggregation_dict))

    agg = cast(QuantityAggregation, agg)
    quantity = validate_quantity(agg.quantity, doc_type=doc_type)
    longest_nested_key = None
    for nested_key in doc_type.nested_object_keys:
        if agg.quantity.startswith(nested_key):
            es_aggs = es_aggs[f'nested_agg:{name}']
            longest_nested_key = nested_key

    has_no_pagination = getattr(agg, 'pagination', None) is None

    if isinstance(agg, BucketAggregation):
        es_agg = es_aggs['agg:' + name]
        values = set()

        def get_bucket(es_bucket) -> Bucket:
            if has_no_pagination:
                if isinstance(agg, DateHistogramAggregation):
                    value = es_bucket['key_as_string']
                else:
                    value = es_bucket['key']
            elif agg.pagination.order_by is None:  # type: ignore
                value = es_bucket.key[name]
            else:
                value = es_bucket.key[quantity.search_field]

            count = es_bucket.doc_count
            metrics = {}
            for metric in agg.metrics:  # type: ignore
                metrics[metric] = es_bucket['metric:' + metric].value

            entries = None
            if 'entries' in es_bucket:
                if longest_nested_key:
                    entries = [{longest_nested_key: item['_source']} for item in es_bucket.entries.hits.hits]
                else:
                    entries = [item['_source'] for item in es_bucket.entries.hits.hits]

            values.add(value)
            if len(metrics) == 0:
                metrics = None
            return Bucket(value=value, entries=entries, count=count, metrics=metrics)

        data = [get_bucket(es_bucket) for es_bucket in es_agg.buckets]

        if has_no_pagination:
            # fill "empty" values
            if quantity.values is not None:
                for value in quantity.values:
                    if value not in values:
                        metrics = {metric: 0 for metric in agg.metrics}
                        if len(metrics) == 0:
                            metrics = None
                        data.append(Bucket(value=value, count=0, metrics=metrics))

        else:
            total = es_aggs['agg:%s:total' % name]['value']
            pagination = PaginationResponse(total=total, **aggregation_dict['pagination'])
            if pagination.page_after_value is not None and pagination.page_after_value.endswith(':'):
                pagination.page_after_value = pagination.page_after_value[0:-1]

            if 'after_key' in es_agg:
                after_key = es_agg['after_key']
                if pagination.order_by is None:
                    pagination.next_page_after_value = after_key[name]
                else:
                    str_values = [str(v) for v in after_key.to_dict().values()]
                    pagination.next_page_after_value = ':'.join(str_values)
            else:
                pagination.next_page_after_value = None

            aggregation_dict['pagination'] = pagination

        if isinstance(agg, TermsAggregation):
            return AggregationResponse(
                terms=TermsAggregationResponse(data=data, **aggregation_dict))
        elif isinstance(agg, HistogramAggregation):
            return AggregationResponse(
                histogram=HistogramAggregationResponse(data=data, **aggregation_dict))
        elif isinstance(agg, DateHistogramAggregation):
            return AggregationResponse(
                date_histogram=DateHistogramAggregationResponse(data=data, **aggregation_dict))
        else:
            raise NotImplementedError()

    if isinstance(agg, MinMaxAggregation):
        min_value = es_aggs['agg:%s:min' % name]['value']
        max_value = es_aggs['agg:%s:max' % name]['value']

        return AggregationResponse(
            min_max=MinMaxAggregationResponse(data=[min_value, max_value], **aggregation_dict))

    raise NotImplementedError()


def _specific_agg(agg: Aggregation) -> Union[TermsAggregation, DateHistogramAggregation, HistogramAggregation, MinMaxAggregation, StatisticsAggregation]:
    if agg.terms is not None:
        return agg.terms

    if agg.histogram is not None:
        return agg.histogram

    if agg.date_histogram is not None:
        return agg.date_histogram

    if agg.min_max is not None:
        return agg.min_max

    if agg.statistics is not None:
        return agg.statistics

    raise NotImplementedError()


def search(
        owner: str = 'public',
        query: Union[Query, EsQuery] = None,
        pagination: MetadataPagination = None,
        required: MetadataRequired = None,
        aggregations: Dict[str, Aggregation] = {},
        user_id: str = None,
        index: Index = entry_index) -> MetadataResponse:

    # The first half of this method creates the ES query. Then the query is run on ES.
    # The second half is about transforming the ES response to a MetadataResponse.

    doc_type = index.doc_type

    # owner
    owner_query = _owner_es_query(owner=owner, user_id=user_id, doc_type=doc_type)

    # query
    if query is None:
        query = {}

    es_query_dict: Dict[str, EsQuery] = {}
    if isinstance(query, EsQuery):
        es_query = cast(EsQuery, query)
    else:
        es_query = validate_api_query(
            cast(Query, query), doc_type=doc_type, owner_query=owner_query,
            results_dict=es_query_dict)

    if doc_type != entry_type:
        owner_query = Q('nested', path='entries', query=owner_query)
    es_query &= owner_query

    # pagination
    if pagination is None:
        pagination = MetadataPagination()

    if pagination.order_by is None:
        pagination.order_by = doc_type.id_field

    search = Search(index=index.index_name)

    # TODO this depends on doc_type
    if pagination.order_by is None:
        pagination.order_by = doc_type.id_field
    order_quantity, page_after_value = validate_pagination(pagination, doc_type=doc_type)
    order_field = order_quantity.search_field
    sort = {order_field: pagination.order.value}
    if order_field != doc_type.id_field:
        sort[doc_type.id_field] = pagination.order.value
    search = search.sort(sort)
    search = search.extra(size=pagination.page_size)

    if pagination.page_offset:
        search = search.extra(**{'from': pagination.page_offset})
    elif pagination.page:
        search = search.extra(**{'from': (pagination.page - 1) * pagination.page_size})
    elif page_after_value:
        search = search.extra(search_after=page_after_value.rsplit(':', 1))

    # required
    if required:
        for list_ in [required.include, required.exclude]:
            for quantity in [] if list_ is None else list_:
                # TODO validate quantities with wildcards
                if '*' not in quantity:
                    validate_quantity(quantity, doc_type=doc_type, loc=['required'])

        if required.include is not None and pagination.order_by not in required.include:
            required.include.append(pagination.order_by)
        if required.exclude is not None and pagination.order_by in required.exclude:
            required.exclude.remove(pagination.order_by)

        if required.include is not None and doc_type.id_field not in required.include:
            required.include.append(doc_type.id_field)

        if required.exclude is not None and doc_type.id_field in required.exclude:
            required.exclude.remove(doc_type.id_field)

        search = search.source(includes=required.include, excludes=required.exclude)

    # aggregations
    aggs = [(name, _specific_agg(agg)) for name, agg in aggregations.items()]
    post_agg_queries: Dict[str, EsQuery] = {}
    excluded_agg_quantities = {
        agg.quantity
        for _, agg in aggs
        if isinstance(agg, QuantityAggregation) and agg.exclude_from_search}

    if len(excluded_agg_quantities) > 0:
        if not isinstance(query, dict):
            # "exclude_from_search" only work for toplevel mapping queries
            raise QueryValidationError(
                f'the query has to be a dictionary if there is an aggregation with exclude_from_search',
                loc=['query'])

        pre_agg_queries = {
            quantity: es_query
            for quantity, es_query in es_query_dict.items()
            if quantity not in excluded_agg_quantities}
        post_agg_queries = {
            quantity: es_query
            for quantity, es_query in es_query_dict.items()
            if quantity in excluded_agg_quantities}

        search = search.post_filter(_create_es_must(post_agg_queries))
        search = search.query(_create_es_must(pre_agg_queries) & owner_query)

    else:
        search = search.query(es_query)  # pylint: disable=no-member

    for name, agg in aggs:
        _api_to_es_aggregation(
            search, name, agg, doc_type=doc_type, post_agg_queries=post_agg_queries)

    # execute
    try:
        es_response = search.execute()
    except RequestError as e:
        raise SearchError(e)
    more_response_data = {}

    # pagination
    next_page_after_value = None
    if 0 < len(es_response.hits) < es_response.hits.total and len(es_response.hits) >= pagination.page_size:
        last = es_response.hits[-1]
        if order_field == doc_type.id_field:
            next_page_after_value = last[doc_type.id_field]
        else:
            # after_value is not necessarily the value stored in the field
            # itself: internally ES can perform the sorting on a different
            # value which is reported under meta.sort.
            after_value = last.meta.sort[0]
            next_page_after_value = '%s:%s' % (after_value, last[doc_type.id_field])
    pagination_response = PaginationResponse(
        total=es_response.hits.total,
        next_page_after_value=next_page_after_value,
        **pagination.dict())

    # aggregations
    if len(aggregations) > 0:
        more_response_data['aggregations'] = cast(Dict[str, Any], {
            name: _es_to_api_aggregation(es_response, name, _specific_agg(agg), doc_type=doc_type)
            for name, agg in aggregations.items()})

    more_response_data['es_query'] = es_query.to_dict()
    if isinstance(query, EsQuery):
        # we cannot report EsQuery back, because it won't validate within the MetadataResponse model
        query = None

    result = MetadataResponse(
        owner='all' if owner is None else owner,
        query=query,
        pagination=pagination_response,
        required=required,
        data=[_es_to_entry_dict(hit, required) for hit in es_response.hits],
        **more_response_data)

    return result


def _index(entries, **kwargs):
    index_entries(entries, **kwargs)


def quantity_values(
        quantity: str, page_size: int = 100, return_buckets: bool = False,
        **kwargs) -> Generator[Any, None, None]:
    '''
    A generator that uses ``search`` and an aggregation to retrieve all
    values of a quantity. Will run multiple requests with page_size until all values
    have been gathered. Kwargs are passed to search, e.g. to change owner or query.
    '''
    page_after_value = None

    while True:
        aggregation = TermsAggregation(quantity=quantity, pagination=AggregationPagination(
            page_size=page_size, page_after_value=page_after_value))

        search_response = search(
            aggregations=dict(value_agg=Aggregation(terms=aggregation)),
            pagination=MetadataPagination(page_size=0),
            **kwargs)

        value_agg = cast(TermsAggregationResponse, search_response.aggregations['value_agg'].terms)  # pylint: disable=no-member
        for bucket in value_agg.data:
            if return_buckets:
                yield bucket
            else:
                yield bucket.value

        if len(value_agg.data) < page_size:
            break

        page_after_value = value_agg.pagination.next_page_after_value
        if page_after_value is None:
            break
