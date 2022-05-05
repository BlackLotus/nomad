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

from nomad.datamodel.data import EntryData
from nomad.metainfo import MSection, Package, Quantity, Datetime
from nomad.units import ureg

m_package = Package(name='material_library')


class ElnBaseSection(MSection):
    name = Quantity(
        type=str,
        description='A short human readable and descriptive name.',
        a_eln=dict(component='StringEditQuantity'))

    lab_id = Quantity(
        type=str,
        description='A id string that is unique at least for the lab that produced this data.',
        a_eln=dict(component='StringEditQuantity'))

    description = Quantity(
        type=str,
        description=(
            'A humand description. This provides room for human readable information '
            'that could not be captured in the ELN.'),
        a_eln=dict(component='RichTextEditQuantity'))

    def normalize(self, archive, logger):
        if isinstance(self, EntryData):
            if archive.data == self and self.name:
                archive.metadata.entry_name = self.name
            EntryData.normalize(self, archive, logger)

        for quantity in self.m_def.all_quantities.values():
            tabular_parser_annotation = quantity.m_annotations.get('tabular_parser', None)
            if tabular_parser_annotation:
                self.tabular_parser(quantity, archive, logger, **tabular_parser_annotation)

    def tabular_parser(self, quantity_def: Quantity, archive, logger, columns, **kwargs):
        if not quantity_def.is_scalar:
            raise NotImplementedError('CSV parser is only implemented for single files.')

        value = self.m_get(quantity_def)
        if not value:
            return

        import pandas as pd
        with archive.m_context.raw_file(self.data_file) as f:
            data = pd.read_csv(f, engine='python', **kwargs)

        for quantity_name, column_value in columns.items():
            quantity = self.m_def.all_quantities[quantity_name]
            if isinstance(column_value, str):
                column_name = column_value
                column_unit = quantity.unit
            elif isinstance(column_value, dict):
                column_name = column_value['name']
                column_unit = ureg(column_value['unit'])

            np_values = data.loc[:, column_name].to_numpy()
            if column_unit is not None:
                np_values *= column_unit
            self.m_set(quantity, np_values)


class ElnActivityBaseSecton(ElnBaseSection):
    datetime = Quantity(
        type=Datetime,
        description='The date and time when this activity was done.',
        a_eln=dict(component='DateTimeEditQuantity'))

    method = Quantity(
        type=str,
        description='A short consistent handle for the applied method.')


class Chemical(ElnBaseSection):
    chemical_formula = Quantity(
        type=str,
        description=(
            'The chemical formula of the chemical. This will be used directly and '
            'indirectly in the search. The formula will be used itself as well as '
            'the extracted chemical elements.'),
        a_eln=dict(component='StringEditQuantity'))


class Sample(ElnBaseSection):
    pass


class Instrument(ElnBaseSection):
    pass


class Process(ElnActivityBaseSecton):
    pass


class Measurement(ElnActivityBaseSecton):
    pass


m_package.__init_metainfo__()
