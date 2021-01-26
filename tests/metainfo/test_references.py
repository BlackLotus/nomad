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

import pytest

from nomad.metainfo import MSection, Quantity, SubSection, MProxy, Reference, QuantityReference


class Referenced(MSection):
    str_quantity = Quantity(type=str)


class Referencing(MSection):
    section_reference = Quantity(type=Referenced)
    section_reference_list = Quantity(type=Referenced, shape=['*'])

    quantity_reference = Quantity(type=Referenced.str_quantity)


class Root(MSection):
    referenced = SubSection(sub_section=Referenced)
    referenceds = SubSection(sub_section=Referenced, repeats=True)
    referencing = SubSection(sub_section=Referencing)


@pytest.fixture(scope='function', params=['reference', 'proxy'])
def definitions(request):
    ''' Alters the type of the references used in the reference properties definitions. '''
    reference_type = request.param
    if reference_type == 'reference':
        Referencing.section_reference.type = Reference(Referenced.m_def)
        Referencing.section_reference_list.type = Reference(Referenced.m_def)
        Referencing.quantity_reference.type = QuantityReference(Referenced.str_quantity)

    elif reference_type == 'proxy':
        Referencing.section_reference.type = Reference(Referenced.m_def)
        Referencing.section_reference_list.type = Reference(Referenced.m_def)
        Referencing.quantity_reference.type = QuantityReference(Referenced.str_quantity)

    else:
        raise NotImplementedError()


@pytest.fixture(scope='function')
def example_data(definitions):
    def create_referenced():
        referenced = Referenced()
        referenced.str_quantity = 'test_value'
        return referenced

    referenced = create_referenced()
    referenced_1 = create_referenced()
    referenced_2 = create_referenced()

    root = Root()
    root.referenced = referenced
    root.m_add_sub_section(Root.referenceds, referenced_1)
    root.m_add_sub_section(Root.referenceds, referenced_2)

    referencing = Referencing()
    referencing.section_reference = referenced
    referencing.section_reference_list = [referenced_1, referenced_2]
    referencing.quantity_reference = referenced
    root.referencing = referencing

    return root


def assert_data(example_data):
    def assert_properties(example_data):
        assert example_data.referencing.section_reference.m_resolved() == example_data.referenced
        assert example_data.referencing.m_to_dict()['section_reference'] == '/referenced'
        assert example_data.referencing.section_reference_list[1].m_resolved() == example_data.referenceds[1]
        assert example_data.referencing.m_to_dict()['section_reference_list'] == ['/referenceds/0', '/referenceds/1']
        assert example_data.referencing.quantity_reference == 'test_value'
        assert example_data.referencing.m_to_dict()['quantity_reference'] == '/referenced/str_quantity'

    assert_properties(example_data)

    example_data_serialized = example_data.m_to_dict(with_meta=True)
    example_data = Root.m_from_dict(example_data_serialized)
    assert_properties(example_data)


def test_references(example_data):
    assert_data(example_data)


def test_section_proxy(example_data):
    example_data.referencing.section_reference = MProxy(
        'doesnotexist',
        m_proxy_section=example_data.referencing,
        m_proxy_quantity=Referencing.section_reference)
    with pytest.raises(ReferenceError):
        example_data.referencing.section_reference.str_quantity

    example_data.referencing.section_reference = MProxy(
        '/referenced',
        m_proxy_section=example_data.referencing,
        m_proxy_quantity=Referencing.section_reference)

    assert_data(example_data)


def test_quantity_proxy(example_data):
    example_data.referencing.quantity_reference = MProxy(
        'doesnotexist',
        m_proxy_section=example_data.referencing,
        m_proxy_quantity=Referencing.section_reference)
    with pytest.raises(ReferenceError):
        example_data.referencing.quantity_reference

    example_data.referencing.quantity_reference = MProxy(
        '/referenced',
        m_proxy_section=example_data.referencing,
        m_proxy_quantity=Referencing.section_reference)
    assert example_data.referencing.quantity_reference == 'test_value'

    assert_data(example_data)
