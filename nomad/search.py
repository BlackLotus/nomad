# Copyright 2018 Markus Scheidgen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an"AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module represents calculations in elastic search.
"""

from typing import Iterable, Dict, List, Any
from elasticsearch_dsl import Document, InnerDoc, Keyword, Text, Date, \
    Object, Boolean, Search, Q, A, analyzer, tokenizer
from elasticsearch_dsl.document import IndexMeta
import elasticsearch.helpers
from elasticsearch.exceptions import NotFoundError
from datetime import datetime

from nomad import config, datamodel, infrastructure, datamodel, coe_repo, utils


path_analyzer = analyzer(
    'path_analyzer',
    tokenizer=tokenizer('path_tokenizer', 'pattern', pattern='/'))


user_cache: Dict[str, Any] = dict()
"""
A cache for user popos used in the index. We will not retrieve names all the time.
This cache should be cleared, before larger re-index operations.
"""


class AlreadyExists(Exception): pass


class ElasticSearchError(Exception): pass


class ScrollIdNotFound(Exception): pass


class User(InnerDoc):

    @classmethod
    def from_user_popo(cls, user):
        self = user_cache.get(user.id, None)
        if self is None:
            self = cls(user_id=user.id)

            if 'first_name' not in user:
                user = coe_repo.User.from_user_id(user.id).to_popo()

            last_name = user['last_name'].strip()
            first_name = user['first_name'].strip()

            if len(last_name) > 0 and len(first_name) > 0:
                name = '%s, %s' % (user['last_name'], user['first_name'])
            elif len(last_name) != 0:
                name = last_name
            elif len(first_name) != 0:
                name = first_name
            else:
                name = 'unnamed user with id %d' % user.id

            self.name = name
            user_cache[user.id] = self

        return self

    user_id = Keyword()
    name = Text(fields={'keyword': Keyword()})


class Dataset(InnerDoc):

    @classmethod
    def from_dataset_popo(cls, dataset):
        return cls(
            id=dataset.id,
            doi=dataset.doi['value'] if dataset.doi is not None else None,
            name=dataset.name)

    id = Keyword()
    doi = Keyword()
    name = Keyword()


class WithDomain(IndexMeta):
    """ Override elasticsearch_dsl metaclass to sneak in domain specific mappings """
    def __new__(cls, name, bases, attrs):
        for quantity in datamodel.Domain.instance.quantities.values():
            attrs[quantity.name] = quantity.elastic_mapping
        return super(WithDomain, cls).__new__(cls, name, bases, attrs)


class Entry(Document, metaclass=WithDomain):

    class Index:
        name = config.elastic.index_name

    upload_id = Keyword()
    upload_time = Date()
    calc_id = Keyword()
    calc_hash = Keyword()
    pid = Keyword()
    mainfile = Keyword()
    files = Text(multi=True, analyzer=path_analyzer, fields={'keyword': Keyword()})
    uploader = Object(User)

    with_embargo = Boolean()
    published = Boolean()

    processed = Boolean()
    last_processing = Date()
    nomad_version = Keyword()
    nomad_commit = Keyword()

    authors = Object(User, multi=True)
    owners = Object(User, multi=True)
    comment = Text()
    references = Keyword()
    datasets = Object(Dataset)

    @classmethod
    def from_calc_with_metadata(cls, source: datamodel.CalcWithMetadata) -> 'Entry':
        entry = Entry(meta=dict(id=source.calc_id))
        entry.update(source)
        return entry

    def update(self, source: datamodel.CalcWithMetadata) -> None:
        self.upload_id = source.upload_id
        self.upload_time = source.upload_time
        self.calc_id = source.calc_id
        self.calc_hash = source.calc_hash
        self.pid = None if source.pid is None else str(source.pid)

        self.processed = source.processed
        self.last_processing = source.last_processing
        self.nomad_version = source.nomad_version
        self.nomad_commit = source.nomad_commit

        self.mainfile = source.mainfile
        if source.files is None:
            self.files = [self.mainfile]
        elif self.mainfile not in source.files:
            self.files = [self.mainfile] + source.files
        else:
            self.files = source.files

        self.uploader = User.from_user_popo(source.uploader) if source.uploader is not None else None

        self.with_embargo = source.with_embargo
        self.published = source.published
        self.authors = [User.from_user_popo(user) for user in source.coauthors]
        self.owners = [User.from_user_popo(user) for user in source.shared_with]
        if self.uploader is not None:
            if self.uploader not in self.authors:
                self.authors.append(self.uploader)
            if self.uploader not in self.owners:
                self.owners.append(self.uploader)
        self.comment = source.comment
        self.references = [ref.value for ref in source.references]
        self.datasets = [Dataset.from_dataset_popo(ds) for ds in source.datasets]

        for quantity in datamodel.Domain.instance.quantities.values():
            setattr(
                self, quantity.name,
                quantity.elastic_value(getattr(source, quantity.metadata_field)))


def delete_upload(upload_id):
    """ Delete all entries with given ``upload_id`` from the index. """
    index = Entry._default_index()
    Search(index=index).query('match', upload_id=upload_id).delete()


def publish(calcs: Iterable[datamodel.CalcWithMetadata]) -> None:
    """ Update all given calcs with their metadata and set ``publish = True``. """
    def elastic_updates():
        for calc in calcs:
            entry = Entry.from_calc_with_metadata(calc)
            entry.published = True
            entry = entry.to_dict(include_meta=True)
            source = entry.pop('_source')
            entry['doc'] = source
            entry['_op_type'] = 'update'
            yield entry

    elasticsearch.helpers.bulk(infrastructure.elastic_client, elastic_updates())
    refresh()


def index_all(calcs: Iterable[datamodel.CalcWithMetadata]) -> None:
    """
    Adds all given calcs with their metadata to the index.

    Returns:
        Number of failed entries.
    """
    def elastic_updates():
        for calc in calcs:
            entry = Entry.from_calc_with_metadata(calc)
            entry = entry.to_dict(include_meta=True)
            entry['_op_type'] = 'index'
            yield entry

    _, failed = elasticsearch.helpers.bulk(infrastructure.elastic_client, elastic_updates(), stats_only=True)
    refresh()
    return failed


def refresh():
    infrastructure.elastic_client.indices.refresh(config.elastic.index_name)


aggregations = datamodel.Domain.instance.aggregations
""" The available aggregations in :func:`aggregate_search` and their maximum aggregation size """

search_quantities = datamodel.Domain.instance.search_quantities
"""The available search quantities """

metrics = {
    'datasets': ('cardinality', 'datasets.id'),
    'unique_code_runs': ('cardinality', 'calc_hash'),
    'users': ('cardinality', 'uploader.name.keyword')
}
"""
The available search metrics. Metrics are integer values given for each entry that can
be used in aggregations, e.g. the sum of all total energy calculations or cardinality of
all unique geometries.
"""

metrics.update(**datamodel.Domain.instance.metrics)

metrics_names = list(metric for metric in metrics.keys())

order_default_quantity = None
for quantity in datamodel.Domain.instance.quantities.values():
    if quantity.order_default:
        order_default_quantity = quantity.name


class SearchRequest:
    '''
    Represents a search request and allows to execute that request.
    It allows to compose the following features: a query;
    statistics (metrics and aggregations); quantity values; scrolling, pagination for entries;
    scrolling for quantity values.

    The query part filters NOMAD data before the other features come into effect. There
    are specialized methods for configuring the :func:`owner` and :func:`time_range` queries.
    Quantity's can be search for by setting them as attributes.

    The aggregations for statistics can be requested for pre-configured quantities. These
    bucket aggregations come with a metric calculated for each each possible
    quantity value.

    The other possible form of aggregations, allows to get quantity values as results
    (e.g. get all datasets, get all users, etc.). Each value can be accompanied by metrics
    (over all entries with that value) and an example value.

    Of course, searches can return a set of search results. Search objects can be
    configured with pagination or scrolling for these results. Pagination is the default
    and also allows ordering of results. Scrolling can be used if all entries need to be
    'scrolled through'. This might be necessary, since elastic search has limits on
    possible pages (e.g. 'from' must by smaller than 10000). On the downside, there is no
    ordering on scrolling.

    There is also scrolling for quantities to go through all quantity values. There is no
    paging for aggregations.
    '''
    def __init__(self, query=None):
        self._query = query
        self._search = Search(index=config.elastic.index_name)

    def owner(self, owner_type: str = 'all', user_id: str = None):
        """
        Uses the query part of the search to restrict the results based on the owner.
        The possible types are: ``all`` for all calculations; ``public`` for
        caclulations visible by everyone, excluding entries only visible to the given user;
        ``user`` for all calculations of to the given user; ``staging`` for all
        calculations in staging of the given user.

        Arguments:
            owner_type: The type of the owner query, see above.
            user_id: The 'owner' given as the user's unique id.

        Raises:
            KeyError: If the given owner_type is not supported
            ValueError: If the owner_type requires a user but none is given, or the
                given user is not allowed to use the given owner_type.
        """
        if owner_type == 'all':
            q = Q('term', published=True) & Q('term', with_embargo=False)
            if user_id is not None:
                q = q | Q('term', owners__user_id=user_id)
        elif owner_type == 'public':
            q = Q('term', published=True) & Q('term', with_embargo=False)
        elif owner_type == 'user':
            if user_id is None:
                raise ValueError('Authentication required for owner value user.')

            q = Q('term', owners__user_id=user_id)
        elif owner_type == 'staging':
            if user_id is None:
                raise ValueError('Authentication required for owner value user')
            q = Q('term', published=False) & Q('term', owners__user_id=user_id)
        elif owner_type == 'admin':
            if user_id is None or not User.is_admin(user_id):
                raise ValueError('This can only be used by the admin user.')
            q = None
        else:
            raise KeyError('Unsupported owner value')

        if q is not None:
            self.q &= q

        return self

    def search_parameters(self, **kwargs):
        """
        Configures the existing query with additional search parameters. Kwargs are
        interpreted as key value pairs. Keys have to coresspond to valid entry quantities
        in the domain's (DFT calculations) datamodel. Alternatively search parameters
        can be set via attributes.
        """
        for name, value in kwargs:
            setattr(self, name, value)

    def __setattr__(self, name, value):
        quantity = search_quantities.get(name, None)
        if quantity is None:
            raise KeyError('Unknown quantity %s' % name)

        if quantity.multi and not isinstance(value, list):
            value = [value]

        value = quantity.elastic_value(value)

        if isinstance(value, list):
            values = value
        else:
            values = [value]

        for item in values:
            q &= Q(quantity.elastic_search_type, **{quantity.elastic_field: item})

        return self

    def time_range(self, start: datetime, end: datetime):
        """ Adds a time range to the query. """
        if start is None and end is None:
            return self

        if start is None:
            start = datetime.fromtimestamp(0)
        if end is None:
            end = datetime.utcnow()

        self.q &= Q('range', upload_time=dict(gte=start, lte=end))

        return self

    @property
    def q(self):
        """ The underlying elasticsearch_dsl query object """
        if self._query is None:
            return Q('match_all')

    @q.setter
    def q(self, q, value):
        self._query = q

    def statistics(
            self, quantities: Dict[str, int] = aggregations,
            metrics_to_use: List[str] = []):
        """
        This can be used to display statistics over the searched entries and allows to
        implement faceted search on the top values for each quantity.

        The metrics contain overall and per quantity value sums of code runs (calcs),
        unique code runs, datasets, and additional domain specific metrics
        (e.g. total energies, and unique geometries for DFTcalculations). The quantities
        that can be aggregated to metrics are defined in module:`datamodel`. Aggregations
        and respective metrics are calculated for aggregations given in ``aggregations``
        and metrics in ``aggregation_metrics``. As a pseudo aggregation ``total_metrics``
        are calculation over all search results. The ``aggregations`` gives tuples of
        quantities and default aggregation sizes.

        The search results will contain a dictionary ``statistics``. This has a key
        for each quantity and an extra key 'total'. Each quantity key will hold a dict
        with a key for each quantity value. Each quantity value key will hold a dict
        with a key for each metric. The values will be the actual aggregated metric values.
        The pseudo quantity 'total' contains a pseudo value 'all'. It is used to
        store the metrics aggregated over all entries in the search results.

        Arguments:
            quantities: A customized list of quantities to aggregate over. Keys are index fields,
                and values the amount of buckets to return. Only works on *keyword* field.
            metrics_to_use: The metrics calculated over the aggregations. Can be
                ``unique_code_runs``, ``datasets``, other domain specific metrics.
                The basic doc_count metric ``code_runs`` is always given.
        """
        for quantity_name, size in quantities.items():
            # We are using elastic searchs 'composite aggregations' here. We do not really
            # compose aggregations, but only those pseudo composites allow us to use the
            # 'after' feature that allows to scan through all aggregation values.
            quantity = search_quantities[quantity_name]
            min_doc_count = 0 if quantity.zero_aggs else 1
            terms = A(
                'terms', field=quantity.elastic_field, size=size, min_doc_count=min_doc_count,
                order=dict(_key='asc'))

            buckets = self._search.aggs.bucket('statistics:%s' % quantity_name, terms)
            if quantity_name not in ['authors']:
                self._add_metrics(buckets, metrics_to_use)

        self._add_metrics(self._search.aggs, metrics_to_use)

        return self

    def _add_metrics(self, parent=None, metrics_to_use: List[str] = []):
        if parent is None:
            parent = self._search.aggs

        for metric in metrics_to_use:
            metric_kind, field = metrics[metric]
            parent.metric(metric, A(metric_kind, field=field))

    def date_histogram(self, metrics_to_use: List[str] = []):
        """
        Adds a date histogram on the given metrics to the statistics part.
        """
        histogram = A('date_histogram', field='upload_time', interval='1M', format='yyyy-MM-dd')
        self._add_metrics(self._search.aggs.bucket('statistics:date_histogram', histogram), metrics_to_use)

        return self

    def quantities(self, **kwargs):
        """
        Shorthand for adding multiple quantities. See :func:`quantity`. Keywork argument
        keys are quantity name, values are tuples of size and after value.
        """
        for name, spec in kwargs:
            size, after = spec
            self.quantity(name, after=after, size=size)

        return self

    def quantity(self, name, size=100, after=None):
        """
        Adds a requests for values of the given quantity.
        It allows to scroll through all values via elasticsearch's
        composite aggregations. The response will contain the quantity values and
        an example entry for each value.

        This can be used to implement continues scrolling through authors, datasets,
        or uploads within the searched entries.

        If one or more quantities are specified,
        the search results will contain a dictionary ``quantities``. The keys are quantity
        name the values dictionary with 'after' and 'values' key.
        The 'values' key holds a dict with all the values as keys and their entry count
        as values (i.e. number of entries with that value).

        Arguments:
            name: The quantity name. Must be in :data:`search_quantities`.
            after: The 'after' value allows to scroll over various requests, by providing
                the 'after' value of the last search. The 'after' value is part of the
                response. Use ``None`` in the first request.
            size:
                The size gives the ammount of maximum values in the next scroll window.
                If the size is None, a maximum of 100 quantity values will be requested.
        """
        if size is None:
            size = 100

        quantity = search_quantities[name]
        terms = A('terms', field=quantity.elastic_field)

        composite = dict(sources={name: terms}, size=size)
        if after is not None:
            composite['after'] = {name: after}

        self._search.aggs.bucket('quantitiy:%s' % name, 'composite', **composite)

        return self

    def execute(self):
        """
        Exectutes without returning actual results. Only makes sense if the request
        was configured for statistics or quantity values.
        """
        return self._response(self._search.execute())

    def execute_scan(self):
        """
        This execute the search as scan. The result will be a generator over the found
        entries. Everything but the query part of this object, will be ignored.
        """
        for hit in self._search.scan():
            yield hit.to_dict()

    def execute_pagenated(
            self, page: int = 1, per_page=10, order_by: str = order_default_quantity,
            order: int = -1):
        """
        Executes the search and returns paginated results. Those are sorted.

        Arguments:
            page: The requested page, starts with 1.
            per_page: The number of entries per page.
            order_by: The quantity to order by.
            order: -1 or 1 for descending or ascending order.
        """
        search = self._search

        if order_by not in search_quantities:
            raise KeyError('Unknown order quantity %s' % order_by)

        order_by_quantity = search_quantities[order_by]

        if order == 1:
            search = search.sort(order_by_quantity.elastic_field)
        else:
            search = search.sort('-%s' % order_by_quantity.elastic_field)
        search = search[(page - 1) * per_page: page * per_page]

        result = self._response(search.execute())
        result.update(pagination=dict(total=result['total'], page=page, per_page=per_page))

    def execute_scrolled(self, scroll_id: str = None, size: int = 1000, scroll: str = u'5m'):
        """
        Executes a scrolling search. based on ES scroll API. Pagination is replaced with
        scrolling, no ordering is available, no statistics, no quantities will be provided.

        Scrolling is done by calling this function again and again with the same ``scroll_id``.
        Each time, this function will return the next batch of search results. If the
        ``scroll_id`` is not available anymore, a new ``scroll_id`` is assigned and scrolling
        starts from the beginning again.

        The response will contain a 'scroll' part with attributes 'total', 'scroll_id',
        and 'size'.

        Arguments:
            scroll_id: The scroll id to receive the next batch from. None will create a new
                scroll.
            size: The batch size in number of hits.
            scroll: The time the scroll should be kept alive (i.e. the time between requests
                to this method) in ES time units. Default is 5 minutes.
        """
        es = infrastructure.elastic_client

        if scroll_id is None:
            # initiate scroll
            resp = es.search(  # pylint: disable=E1123
                body=self._search.to_dict(), scroll=scroll, size=size,
                index=config.elastic.index_name)

            scroll_id = resp.get('_scroll_id')
            if scroll_id is None:
                # no results for search query
                return dict(scroll=dict(total=0, size=size), results=[])

        else:
            try:
                resp = es.scroll(scroll_id, scroll=scroll)  # pylint: disable=E1123
            except NotFoundError:
                raise ScrollIdNotFound()

        total = resp['hits']['total']
        results = list(hit['_source'] for hit in resp['hits']['hits'])

        # since we are using the low level api here, we should check errors
        if resp["_shards"]["successful"] < resp["_shards"]["total"]:
            utils.get_logger(__name__).error('es operation was unsuccessful on at least one shard')
            raise ElasticSearchError('es operation was unsuccessful on at least one shard')

        if len(results) == 0:
            es.clear_scroll(body={'scroll_id': [scroll_id]}, ignore=(404, ))  # pylint: disable=E1123
            scroll_id = None

        scroll_info = dict(total=total, size=size)
        if scroll_id is not None:
            scroll_info.update(scroll_id=scroll_id)

        return dict(scroll=scroll_info, results=results)

    def _response(self, response) -> Dict[str, Any]:
        result: Dict[str, Any] = dict()

        total = response.hits.total if hasattr(response, 'hits') else 0
        result.update(total=total)

        # hits
        result.update(results=[hit.to_dict() for hit in response.hits])

        # statistics
        def get_metrics(bucket, code_runs):
            result = {
                metric: bucket[metric]['value']
                for metric in vars(bucket)
            }
            result.update(code_runs=code_runs)
            return result

        metrics_results = {
            quantity_name: {
                bucket.key: get_metrics(bucket, bucket.doc_count)
                for bucket in getattr(response.aggregations, quantity_name).buckets
            }
            for quantity_name in vars(response.aggrgations)
            if quantity_name.startswith('statistics:')
        }

        total_metrics_result = get_metrics(response.aggregations, total)
        metrics_results['total'] = dict(all=total_metrics_result)
        result.update(quantities=metrics_results)

        # quantities
        def create_quantity_result(quantity):
            values = getattr(response.aggregations, quantity)
            result = dict(values={
                getattr(bucket.key, quantity): bucket.doc_count
                for bucket in values.buckets})

            if hasattr(values, 'after_key'):
                result.update(after=getattr(values.after_key, quantity))

            return result

        quantity_results = {
            quantity: create_quantity_result(quantity)
            for quantity_name in vars(response.aggrgations)
            if quantity_name.startswith('statistics:')
        }

        result.update(quantities=quantity_results)

        return result
