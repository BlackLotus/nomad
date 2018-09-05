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

from abc import ABCMeta, abstractmethod
from typing import List, Dict, Any

from nomad.parsing import AbstractParserBackend
from nomad.utils import get_logger

logger = get_logger(__name__)

s_system = 'section_system'
s_scc = 'section_single_configuration_calculation'
s_frame_sequence = 'section_frame_sequence'
r_scc_to_system = 'single_configuration_calculation_to_system_ref'
r_frame_sequence_local_frames = 'frame_sequence_local_frames_ref'


class Normalizer(metaclass=ABCMeta):
    """
    A base class for normalizers. Normalizers work on a :class:`AbstractParserBackend` instance
    for read and write.

    Arguments:
        backend: the backend used to read and write data from and to
    """
    def __init__(self, backend: AbstractParserBackend) -> None:

        self._backend = backend

    @abstractmethod
    def normalize(self) -> None:
        pass


class SystemBasedNormalizer(Normalizer, metaclass=ABCMeta):
    """
    A normalizer base class for normalizers that only touch a section_system.

    The normalizer is either run on all section systems or only  for systems that are
    linked to a section_single_configuration_calculation. Also if there are multiple sccs,
    the normalizer is only run for the last frame belonging to a frame sequence.

    Arguments:
        all_sections: apply normalizer to all section_system instances or only the
            last single config calc of the last frame sequence
    """
    def __init__(self, backend: AbstractParserBackend, all_sections=True) -> None:
        super().__init__(backend=backend)
        self._all_sections = all_sections

    @property
    def quantities(self) -> List[str]:
        return [
            'atom_labels',
            'atom_positions',
            'atom_atom_numbers',
            'lattice_vectors',
            'simulation_cell',
            'configuration_periodic_dimensions'
        ]

    def _normalize_system(self, g_index):
        input_data = dict(
            uri='/section_run/0/section_system/%d' % g_index,
            gIndex=g_index)
        for quantity in self.quantities:
            try:
                input_data[quantity] = self._backend.get_value(quantity, g_index)
            except KeyError:
                # only fail when the normalizer actually uses the respecitive value
                pass

        context = input_data['uri']
        self._backend.openContext(context)
        try:
            self.normalize_system(input_data)
        finally:
            self._backend.closeContext(context)

    @abstractmethod
    def normalize_system(self, section_system: Dict[str, Any]) -> None:
        pass

    def normalize(self) -> None:
        if self._all_sections:
            systems = self._backend.get_sections(s_system)
        else:
            # look for sccs in last frames
            sccs = []
            for frame_seq in self._backend.get_sections(s_frame_sequence):
                frames = self._backend.get_value(r_frame_sequence_local_frames, frame_seq)
                if len(frames) > 0:
                    sccs.append(frames[-1])

            # no sccs from frames -> consider all sccs
            if len(sccs) == 0:
                sccs = self._backend.get_sections(s_scc)

            # no sccs -> consider all systems
            systems = [self._backend.get_value(r_scc_to_system, scc) for scc in sccs]

            # only take the first, and last two systems
            if len(systems) == 0:
                systems = self._backend.get_sections(s_system)
                if len(systems) > 2:
                    systems = [systems[0], systems[-2], systems[-1]]

        for g_index in systems:
            try:
                self._normalize_system(g_index)
            except KeyError as e:
                logger.error(
                    'Could not read all input data', normalizer=self.__class__.__name__,
                    section='section_system', g_index=g_index, key_error=str(e))
            except Exception as e:
                logger.error(
                    'Unexpected error during normalizing', normalizer=self.__class__.__name__,
                    section='section_system', g_index=g_index, exc_info=e)
                raise e
