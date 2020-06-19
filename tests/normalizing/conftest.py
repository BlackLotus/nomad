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

import pytest

from ase import Atoms

from nomad.parsing.legacy import Backend
from nomad.normalizing import normalizers

from tests.test_parsing import parsed_vasp_example  # pylint: disable=unused-import
from tests.test_parsing import parsed_template_example  # pylint: disable=unused-import
from tests.test_parsing import parsed_example  # pylint: disable=unused-import
from tests.test_parsing import parse_file
from tests.test_parsing import parsed_template_no_system  # pylint: disable=unused-import


def run_normalize(backend: Backend) -> Backend:
    status, _ = backend.status

    assert status == 'ParseSuccess'

    for normalizer_class in normalizers:
        normalizer = normalizer_class(backend)
        normalizer.normalize()
    return backend


@pytest.fixture
def normalized_vasp_example(parsed_vasp_example: Backend) -> Backend:
    return run_normalize(parsed_vasp_example)


@pytest.fixture
def normalized_example(parsed_example: Backend) -> Backend:
    return run_normalize(parsed_example)


@pytest.fixture
def normalized_template_example(parsed_template_example) -> Backend:
    return run_normalize(parsed_template_example)


def run_normalize_for_structure(atoms: Atoms) -> Backend:
    template = parsed_template_no_system()

    # Fill structural information
    gid = template.openSection("section_system")
    template.addArrayValues("atom_positions", atoms.get_positions() * 1E-10)
    template.addArrayValues("atom_labels", atoms.get_chemical_symbols())
    template.addArrayValues("simulation_cell", atoms.get_cell() * 1E-10)
    template.addArrayValues("configuration_periodic_dimensions", atoms.get_pbc())
    template.closeSection("section_system", gid)

    return run_normalize(template)


@pytest.fixture(scope='session')
def single_point(two_d) -> Backend:
    return two_d


@pytest.fixture(scope='session')
def gw(two_d) -> Backend:
    parser_name = "parsers/template"
    filepath = "tests/data/normalizers/gw.json"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def geometry_optimization() -> Backend:
    parser_name = "parsers/template"
    filepath = "tests/data/normalizers/fcc_crystal_structure.json"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def molecular_dynamics(bulk) -> Backend:
    return bulk


@pytest.fixture(scope='session')
def phonon() -> Backend:
    parser_name = "parsers/phonopy"
    filepath = "tests/data/parsers/phonopy/phonopy-FHI-aims-displacement-01/control.in"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def bulk() -> Backend:
    parser_name = "parsers/cp2k"
    filepath = "tests/data/normalizers/cp2k_bulk_md/si_md.out"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def two_d() -> Backend:
    parser_name = "parsers/fhi-aims"
    filepath = "tests/data/normalizers/fhiaims_2d_singlepoint/aims.out"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def surface() -> Backend:
    parser_name = "parsers/fhi-aims"
    filepath = "tests/data/normalizers/fhiaims_surface_singlepoint/PBE-light+tight-rho2.out"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def molecule() -> Backend:
    parser_name = "parsers/fhi-aims"
    filepath = "tests/data/normalizers/fhiaims_molecule_singlepoint/aims.out"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def atom() -> Backend:
    parser_name = "parsers/gaussian"
    filepath = "tests/data/normalizers/gaussian_atom_singlepoint/m9b7.out"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def one_d() -> Backend:
    parser_name = "parsers/exciting"
    filepath = "tests/data/normalizers/exciting_1d_singlepoint/INFO.OUT"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def bands_unpolarized_gap_indirect() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/unpolarized_gap/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def bands_polarized_no_gap() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/polarized_no_gap/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def bands_unpolarized_no_gap() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/unpolarized_no_gap/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def bands_polarized_gap_indirect() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/polarized_gap/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def dos_polarized_vasp() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/dos/polarized_vasp/vasprun.xml.relax2.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def dos_unpolarized_vasp() -> Backend:
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/dos/unpolarized_vasp/vasprun.xml.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def hash_exciting() -> Backend:
    parser_name = "parsers/exciting"
    filepath = "tests/data/normalizers/hashes/exciting/INFO.OUT"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def hash_vasp(bands_unpolarized_gap_indirect) -> Backend:
    return bands_unpolarized_gap_indirect


@pytest.fixture(scope='session')
def band_path_cF(bands_unpolarized_gap_indirect) -> Backend:
    """Band structure calculation for a cP Bravais lattice.
    """
    return bands_unpolarized_gap_indirect


@pytest.fixture(scope='session')
def band_path_tP() -> Backend:
    """Band structure calculation for a tP Bravais lattice.
    """
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/tP/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def band_path_hP() -> Backend:
    """Band structure calculation for a hP Bravais lattice.
    """
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/hP/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def band_path_mP_nonstandard() -> Backend:
    """Band structure calculation for a mP Bravais lattice with a non-standard
    lattice ordering.
    """
    parser_name = "parsers/vasp"
    filepath = "tests/data/normalizers/band_structure/mP_nonstandard/vasprun.xml.bands.xz"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend


@pytest.fixture(scope='session')
def band_path_cF_nonstandard() -> Backend:
    """Band structure calculation for a mP Bravais lattice with a non-standard
    lattice ordering.
    """
    parser_name = "parsers/exciting"
    filepath = "tests/data/normalizers/band_structure/cF_nonstandard/INFO.OUT"
    backend = parse_file((parser_name, filepath))
    backend = run_normalize(backend)
    return backend