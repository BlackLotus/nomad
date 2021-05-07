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

import os.path

from nomad import config, datamodel

from .parser import MissingParser, BrokenParser, Parser, ArchiveParser
from .legacy import LegacyParser
from .artificial import EmptyParser, GenerateRandomParser, TemplateParser, ChaosParser

from eelsdbconverter import EELSApiJsonConverter
from mpesparser import MPESParser
from aptfimparser import APTFIMParser
from vaspparser import VASPParser
from phonopyparser import PhonopyParser
from elasticparser import ElasticParser
from lammpsparser import LammpsParser
from gromacsparser import GromacsParser
from crystalparser import CrystalParser
from fhiaimsparser import FHIAimsParser
from excitingparser import ExcitingParser
from abinitparser import AbinitParser
from quantumespressoparser import QuantumEspressoParser
from gaussianparser import GaussianParser
from gpawparser import GPAWParser
from octopusparser import OctopusParser
from orcaparser import OrcaParser
from cp2kparser import CP2KParser
from fhivibesparser import FHIVibesParser
from turbomoleparser import TurbomoleParser
from castepparser import CastepParser
from wien2kparser import Wien2kParser
from nwchemparser import NWChemParser
from bandparser import BandParser
from amberparser import AmberParser
from asapparser import AsapParser
from bigdftparser import BigDFTParser
from cpmdparser import CPMDParser

try:
    # these packages are not available without parsing extra, which is ok, if the
    # parsers are only initialized to load their metainfo definitions
    import magic
    import gzip
    import bz2
    import lzma

    _compressions = {
        b'\x1f\x8b\x08': ('gz', gzip.open),
        b'\x42\x5a\x68': ('bz2', bz2.open),
        b'\xfd\x37\x7a': ('xz', lzma.open)
    }

    encoding_magic = magic.Magic(mime_encoding=True)

except ImportError:
    pass


def match_parser(mainfile_path: str, strict=True) -> Parser:
    '''
    Performs parser matching. This means it take the given mainfile and potentially
    opens it with the given callback and tries to identify a parser that can parse
    the file.

    This is determined by filename (e.g. *.out), mime type (e.g. text/*, application/xml),
    and beginning file contents.

    Arguments:
        mainfile_path: Path to the mainfile
        strict: Only match strict parsers, e.g. no artificial parsers for missing or empty entries.

    Returns: The parser, or None if no parser could be matched.
    '''
    mainfile = os.path.basename(mainfile_path)
    if mainfile.startswith('.') or mainfile.startswith('~'):
        return None

    with open(mainfile_path, 'rb') as f:
        compression, open_compressed = _compressions.get(f.read(3), (None, open))

    with open_compressed(mainfile_path, 'rb') as cf:  # type: ignore
        buffer = cf.read(config.parser_matching_size)

    mime_type = magic.from_buffer(buffer, mime=True)

    decoded_buffer = None
    encoding = None
    try:  # Try to open the file as a string for regex matching.
        decoded_buffer = buffer.decode('utf-8')
    except UnicodeDecodeError:
        # This file is either binary or has wrong encoding
        encoding = encoding_magic.from_buffer(buffer)

        if config.services.force_raw_file_decoding:
            encoding = 'iso-8859-1'

        if encoding in ['iso-8859-1']:
            try:
                decoded_buffer = buffer.decode(encoding)
            except Exception:
                pass

    for parser in parsers:
        if strict and isinstance(parser, (MissingParser, EmptyParser)):
            continue

        if parser.is_mainfile(mainfile_path, mime_type, buffer, decoded_buffer, compression):
            # potentially convert the file
            if encoding in ['iso-8859-1']:
                try:
                    with open(mainfile_path, 'rb') as binary_file:
                        content = binary_file.read().decode(encoding)
                except Exception:
                    pass
                else:
                    with open(mainfile_path, 'wt') as text_file:
                        text_file.write(content)

            # TODO: deal with multiple possible parser specs
            return parser

    return None


parsers = [
    GenerateRandomParser(),
    TemplateParser(),
    ChaosParser(),
    PhonopyParser(),
    VASPParser(),
    ExcitingParser(),
    FHIAimsParser(),
    FHIVibesParser(),
    CP2KParser(),
    CrystalParser(),
    # The main contents regex of CPMD was causing a catostrophic backtracking issue
    # when searching through the first 500 bytes of main files. We decided
    # to use only a portion of the regex to avoid that issue.
    CPMDParser(),
    NWChemParser(),
    BigDFTParser(),
    Wien2kParser(),
    BandParser(),
    QuantumEspressoParser(),
    GaussianParser(),
    AbinitParser(),
    OrcaParser(),
    CastepParser(),
    LegacyParser(
        name='parsers/dl-poly', code_name='DL_POLY', code_homepage='https://www.scd.stfc.ac.uk/Pages/DL_POLY.aspx',
        parser_class_name='dlpolyparser.DlPolyParserWrapper',
        mainfile_contents_re=(r'\*\* DL_POLY \*\*')
    ),
    LegacyParser(
        name='parsers/lib-atoms', code_name='libAtoms', code_homepage='https://libatoms.github.io/',
        parser_class_name='libatomsparser.LibAtomsParserWrapper',
        mainfile_contents_re=(r'\s*<GAP_params\s')
    ),
    OctopusParser(),
    GPAWParser(),
    LegacyParser(
        name='parsers/atk', code_name='AtomistixToolKit', code_homepage='https://www.synopsys.com/silicon/quantumatk.html',
        parser_class_name='atkparser.ATKParserWrapper',
        # mainfile_contents_re=r'',  # We can't read .gpw as txt - of UlmGPAW|AFFormatGPAW'
        mainfile_name_re=r'^.*\.nc',
        # The previously used mime type r'application/x-netcdf' wasn't found by magic library.
        mainfile_mime_re=r'application/octet-stream'
    ),
    LegacyParser(
        name='parsers/gulp', code_name='gulp', code_homepage='http://gulp.curtin.edu.au/gulp/',
        parser_class_name='gulpparser.GULPParser',
        mainfile_contents_re=(
            r'\s*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*'
            r'\*\*\*\*\*\*\*\*\*\*\*\*\*\s*'
            r'\s*\*\s*GENERAL UTILITY LATTICE PROGRAM\s*\*\s*')
    ),
    LegacyParser(
        name='parsers/siesta', code_name='Siesta', code_homepage='https://departments.icmab.es/leem/siesta/',
        parser_class_name='siestaparser.SiestaParser',
        mainfile_contents_re=(
            r'(Siesta Version: siesta-|SIESTA [0-9]\.[0-9]\.[0-9])|'
            r'(\*\s*WELCOME TO SIESTA\s*\*)')
    ),
    LegacyParser(
        name='parsers/elk', code_name='elk', code_homepage='http://elk.sourceforge.net/',
        parser_class_name='elkparser.ElkParser',
        mainfile_contents_re=r'\| Elk version [0-9.a-zA-Z]+ started \|'
    ),
    ElasticParser(),
    LegacyParser(
        name='parsers/gamess', code_name='GAMESS', code_homepage='https://www.msg.chem.iastate.edu/gamess/versions.html',
        parser_class_name='gamessparser.GamessParser',
        mainfile_contents_re=(
            r'\s*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\**\s*'
            r'\s*\*\s*GAMESS VERSION =\s*(.*)\*\s*'
            r'\s*\*\s*FROM IOWA STATE UNIVERSITY\s*\*\s*')
    ),
    TurbomoleParser(),
    MPESParser(),
    APTFIMParser(),
    EELSApiJsonConverter(),
    LegacyParser(
        name='parsers/qbox', code_name='qbox', code_homepage='http://qboxcode.org/', domain='dft',
        parser_class_name='qboxparser.QboxParser',
        mainfile_mime_re=r'(application/xml)|(text/.*)',
        mainfile_contents_re=(r'http://qboxcode.org')
    ),
    LegacyParser(
        name='parsers/dmol', code_name='DMol3', code_homepage='http://dmol3.web.psi.ch/dmol3.html', domain='dft',
        parser_class_name='dmol3parser.Dmol3Parser',
        mainfile_name_re=r'.*\.outmol',
        mainfile_contents_re=r'Materials Studio DMol\^3'
    ),
    LegacyParser(
        name='parsers/fleur', code_name='fleur', code_homepage='https://www.flapw.de/', domain='dft',
        parser_class_name='fleurparser.FleurParser',
        mainfile_contents_re=r'This output is generated by fleur.'
    ),
    LegacyParser(
        name='parsers/molcas', code_name='MOLCAS', code_homepage='http://www.molcas.org/', domain='dft',
        parser_class_name='molcasparser.MolcasParser',
        mainfile_contents_re=r'M O L C A S'
    ),
    LegacyParser(
        name='parsers/onetep', code_name='ONETEP', code_homepage='https://www.onetep.org/', domain='dft',
        parser_class_name='onetepparser.OnetepParser',
        mainfile_contents_re=r'####### #     # ####### ####### ####### ######'
    ),
    LegacyParser(
        name='parsers/openkim', code_name='OpenKIM', domain='dft',
        parser_class_name='openkimparser.OpenKIMParser',
        mainfile_contents_re=r'OPENKIM'
    ),
    LegacyParser(
        name='parsers/tinker', code_name='TINKER', domain='dft',
        parser_class_name='tinkerparser.TinkerParser',
        mainfile_contents_re=r'TINKER  ---  Software Tools for Molecular Design'
    ),
    LammpsParser(),
    AmberParser(),
    GromacsParser(),
    LegacyParser(
        name='parsers/gromos', code_name='Gromos', domain='dft',
        parser_class_name='gromosparser.GromosParser',
        mainfile_contents_re=r'Bugreports to http://www.gromos.net'
    ),
    LegacyParser(
        name='parsers/namd', code_name='Namd', domain='dft',
        parser_class_name='namdparser.NamdParser',
        mainfile_contents_re=r'\s*Info:\s*NAMD\s*[0-9.]+\s*for\s*',
        mainfile_mime_re=r'text/.*',
    ),
    LegacyParser(
        name='parsers/charmm', code_name='Charmm', domain='dft',
        parser_class_name='charmmparser.CharmmParser',
        mainfile_contents_re=r'\s*Chemistry\s*at\s*HARvard\s*Macromolecular\s*Mechanics\s*',
        mainfile_mime_re=r'text/.*',
    ),
    LegacyParser(
        name='parsers/dftbplus', code_name='DFTB+', domain='dft',
        parser_class_name='dftbplusparser.DFTBPlusParser',
        mainfile_contents_re=r'^ Fermi distribution function\s*',
        mainfile_mime_re=r'text/.*',
    ),
    AsapParser(),
    LegacyParser(
        name='parsers/fplo', code_name='fplo', domain='dft',
        parser_class_name='fploparser.FploParser',
        mainfile_contents_re=r'\s*\|\s*FULL-POTENTIAL LOCAL-ORBITAL MINIMUM BASIS BANDSTRUCTURE CODE\s*\|\s*',
        mainfile_mime_re=r'text/.*',
    ),
    LegacyParser(
        name='parsers/mopac', code_name='MOPAC', domain='dft',
        parser_class_name='mopacparser.MopacParser',
        mainfile_contents_re=r'\s*\*\*\s*MOPAC\s*([0-9a-zA-Z]*)\s*\*\*\s*',
        mainfile_mime_re=r'text/.*',
    ),
    ArchiveParser()
]

empty_parsers = [
    EmptyParser(
        name='missing/octopus', code_name='Octopus', code_homepage='https://octopus-code.org/',
        domain='dft',
        mainfile_name_re=r'(inp)|(.*/inp)'
    ),
    EmptyParser(
        name='missing/crystal', code_name='Crystal', code_homepage='https://www.crystal.unito.it/index.php',
        domain='dft',
        mainfile_name_re=r'.*\.cryst\.out'
    ),
    EmptyParser(
        name='missing/wien2k', code_name='WIEN2k', code_homepage='http://www.wien2k.at/',
        domain='dft',
        mainfile_name_re=r'.*\.scf'
    ),
    EmptyParser(
        name='missing/fhi-aims', code_name='FHI-aims', code_homepage='https://aimsclub.fhi-berlin.mpg.de/',
        domain='dft',
        mainfile_name_re=r'.*\.fhiaims'
    )
]

if config.use_empty_parsers:
    # There are some entries with PIDs that have mainfiles which do not match what
    # the actual parsers expect. We use the EmptyParser to produce placeholder entries
    # to keep the PIDs. These parsers will not match for new, non migrated data.
    parsers.extend(empty_parsers)

parsers.append(BrokenParser())

''' Instantiation and constructor based config of all parsers. '''

parser_dict = {parser.name: parser for parser in parsers + empty_parsers}  # type: ignore
''' A dict to access parsers by name. Usually 'parsers/<...>', e.g. 'parsers/vasp'. '''

# renamed parsers
parser_dict['parser/broken'] = parser_dict['parsers/broken']
parser_dict['parser/fleur'] = parser_dict['parsers/fleur']
parser_dict['parser/molcas'] = parser_dict['parsers/molcas']
parser_dict['parser/octopus'] = parser_dict['parsers/octopus']
parser_dict['parser/onetep'] = parser_dict['parsers/onetep']

# register code names as possible statistic value to the dft datamodel
code_names = []
for parser in parsers:
    if parser.domain == 'dft' and \
            getattr(parser, 'code_name', None) is not None and \
            getattr(parser, 'code_name') != 'currupted mainfile' and \
            getattr(parser, 'code_name') != 'Template':
        code_names.append(getattr(parser, 'code_name'))
code_names = sorted(set(code_names), key=lambda code_name: code_name.lower())
datamodel.DFTMetadata.code_name.a_search.statistic_values = code_names + [
    config.services.unavailable_value, config.services.not_processed_value]
