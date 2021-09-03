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

''' Methods to help with testing of nomad@FAIRDI.'''

from typing import List, Union, Dict, Any
import urllib.parse
import json
from logging import LogRecord
from datetime import datetime, timedelta
import zipfile
import os.path

from nomad import search, files
from nomad.datamodel import EntryMetadata, EntryArchive, DFTMetadata, Results
from nomad.datamodel.metainfo.simulation.run import Run, Program
from nomad.datamodel.metainfo.simulation.system import System, Atoms
from tests.normalizing.conftest import run_normalize


def assert_log(caplog, level: str, event_part: str) -> LogRecord:
    '''
    Assert whether a log message exists in the logs of the tests at a certain level.

    Parameters
    ----------
    caplog : pytest fixture
        This informs pytest that we want to access the logs from a pytest test.
    level : str
        The level of type of log for which we will search (e.g. 'WARN',
        'ERROR', 'DEBUG').
    event_part : str
        The error message we're after. We search the logs matching level if they
        contain this string.

    '''
    record = None
    for record in caplog.get_records(when='call'):
        if record.levelname == level:
            try:
                event_data = json.loads(record.msg)
                present = event_part in event_data['event']
            except Exception:
                present = event_part in record.msg

            if present:
                record = record
                # No need to look for more matches since we aren't counting matches.
                break
    assert record is not None

    return record


def assert_at_least(source, target):
    '''
    Compares two dicts recursively and asserts that all information in source equals
    the same information in target. Additional information in target is ignored.
    '''
    for key, value in source.items():
        assert key in target, '%s with value %s in %s is not in %s' % (key, source[key], source, target)
        if isinstance(value, dict):
            assert_at_least(value, target[key])
        else:
            assert value == target[key], '%s with value %s in %s is not equal the target value %s in %s' % (
                key, source[key], source, target[key], target)


def assert_url_query_args(url: str, **kwargs):
    '''
    Parses the url, and checks that the query arguments match the values specified by kwargs.
    '''
    __, __, __, __, query, __ = urllib.parse.urlparse(url)
    query_dict = urllib.parse.parse_qs(query)
    for k, v in kwargs.items():
        if v is None:
            assert k not in query_dict
        else:
            assert query_dict[k][0] == str(v)


def build_url(base_url: str, query_args: Dict[str, Any]) -> str:
    '''
    Takes a base_url and a dictionary, and combines to a url with query arguments.
    Arguments with value None are ignored.
    '''
    # Remove args with value None
    query_args_clean = {k: v for k, v in query_args.items() if v is not None}
    if not query_args_clean:
        return base_url
    return base_url + '?' + urllib.parse.urlencode(query_args_clean, doseq=True)


def set_upload_entry_metadata(upload, metadata: Dict[str, Any]):
    '''
    Sets the provided metadata values on all entries of the given upload.
    '''
    from nomad import processing as proc
    for entry in proc.Calc.objects(upload_id=upload.upload_id):
        entry.metadata.update(metadata)
        entry.save()


class ExampleData:
    '''
    Allows to define, create, and manage a set of example data. Will create respective
    data via raw files, archives, in mongodb, and in both elasticsearch indices.

    Requires initialized infrastructure.

    Attributes:
        uploads: A dictionary with with upload_ids as keys and lists of entry_ids as values.
        entries: A dictionary with entry_ids as keys and their ``EntryMetadata`` as values.
        archives: A dictionary with entry_ids as keys and their ``EntryArchives`` as values.
    '''

    def __init__(self, **kwargs):
        self.upload_entries: Dict[str, List[str]] = dict()
        self.uploads: Dict[str, Dict[str, Any]] = dict()
        self.entries: Dict[str, EntryMetadata] = dict()
        self.archives: Dict[str, EntryArchive] = dict()

        self.entry_defaults = kwargs
        self._entry_id_counter = 1
        self._upload_id_counter = 1

        self._time_stamp = datetime.utcnow()

    def save(self, with_files: bool = True, with_mongo: bool = True, with_es: bool = True):
        from tests.test_files import create_test_upload_files
        from nomad import processing as proc

        if with_mongo:
            for upload_id, upload_dict in self.uploads.items():
                mongo_upload = proc.Upload(**upload_dict)
                mongo_upload.save()

            for entry_metadata in self.entries.values():
                mongo_entry = proc.Calc(
                    create_time=self._next_time_stamp(),
                    calc_id=entry_metadata.calc_id,
                    upload_id=entry_metadata.upload_id,
                    mainfile=entry_metadata.mainfile,
                    parser='parsers/vasp',
                    process_status=proc.ProcessStatus.SUCCESS)
                upload_dict = self.uploads.get(entry_metadata.upload_id)
                if upload_dict:
                    # Mirror fields from upload
                    entry_metadata.uploader = upload_dict['user_id']
                    entry_metadata.upload_time = upload_dict['upload_time']
                mongo_entry.apply_entry_metadata(entry_metadata)
                mongo_entry.save()

        if with_es:
            archives = list(self.archives.values())
            search.index(archives, update_materials=True, refresh=True)

        if with_files:
            for upload_id in set(list(self.uploads) + list(self.upload_entries)):
                entry_ids = self.upload_entries.get(upload_id, [])
                published = self.uploads.get(upload_id, {}).get('published', True)
                if len(entry_ids) > 0:
                    published = True
                archives = []
                for entry_id in entry_ids:
                    published &= self.entries[entry_id].published
                    if entry_id in self.archives:
                        archives.append(self.archives[entry_id])

                create_test_upload_files(upload_id, archives, published=published)
                from nomad import files
                assert files.UploadFiles.get(upload_id) is not None

    def delete(self):
        from nomad import processing as proc

        for upload_id in self.upload_entries:
            search.delete_upload(upload_id, refresh=True)
            upload_proc = proc.Upload.objects(upload_id=upload_id).first()
            if upload_proc is not None:
                upload_proc.delete()
            upload_files = files.UploadFiles.get(upload_id)
            if upload_files is not None:
                upload_files.delete()

    def create_upload(self, upload_id, **kwargs):
        '''
        Creates a dictionary holding all the upload information.
        Default values are used/generated, and can be set via kwargs.
        '''
        upload_dict = {
            'upload_id': upload_id,
            'current_process': 'process_upload',
            'process_status': 'SUCCESS',
            'errors': [],
            'warnings': [],
            'create_time': self._next_time_stamp(),
            'upload_time': self._next_time_stamp(),
            'complete_time': self._next_time_stamp(),
            'last_update': self._next_time_stamp(),
            'embargo_length': 0,
            'published': False,
            'published_to': []}
        upload_dict.update(kwargs)
        if upload_dict['published'] and 'publish_time' not in upload_dict:
            upload_dict['publish_time'] = self._next_time_stamp()
        if 'user_id' not in upload_dict and 'uploader' in self.entry_defaults:
            upload_dict['user_id'] = self.entry_defaults['uploader'].user_id
        self.uploads[upload_id] = upload_dict

    def create_entry(
            self,
            entry_archive: EntryArchive = None,
            calc_id: str = None, entry_id: str = None, upload_id: str = None,
            material_id: str = None,
            mainfile: str = None,
            results: Union[Results, dict] = None,
            dft: Union[DFTMetadata, dict] = None,
            archive: dict = None, **kwargs):

        if entry_id is None:
            entry_id = calc_id

        if entry_id is None:
            entry_id = f'test_entry_id_{self._entry_id_counter}'
            self._entry_id_counter += 1

        if mainfile is None:
            mainfile = f'mainfile_for_{entry_id}'

        if upload_id is None:
            upload_id = f'test_upload_id_{self._upload_id_counter}'
            self._upload_id_counter += 1

        if entry_archive is None:
            entry_archive = EntryArchive()

        if material_id is None:
            material_id = 'test_material_id'

        entry_metadata = entry_archive.metadata
        if entry_metadata is None:
            entry_metadata = entry_archive.m_create(EntryMetadata)

        upload_time = None
        if upload_id in self.uploads:
            upload_time = self.uploads[upload_id].get('upload_time')
        if upload_time is None:
            upload_time = self._next_time_stamp()

        entry_metadata.m_update(
            calc_id=entry_id,
            upload_id=upload_id,
            mainfile=mainfile,
            calc_hash='dummy_hash_' + entry_id,
            domain='dft',
            upload_time=upload_time,
            published=True,
            processed=True,
            with_embargo=False,
            parser_name='parsers/vasp')
        entry_metadata.m_update(**self.entry_defaults)
        entry_metadata.m_update(**kwargs)

        # create v0 default data
        if entry_archive.metadata.dft is None:
            if dft is None:
                dft = {
                    'xc_functional': 'GGA',
                    'code_name': 'VASP',
                    'n_calculations': 1,
                    'atoms': ['H', 'O'],
                    'n_atoms': 2
                }
            if isinstance(dft, dict):
                for key in ['atoms', 'n_atoms']:
                    if key in dft:
                        setattr(entry_metadata, key, dft.pop(key))
                section_dft = DFTMetadata.m_from_dict(dft)
            else:
                section_dft = dft
            assert isinstance(section_dft, DFTMetadata)
            entry_metadata.m_add_sub_section(EntryMetadata.dft, section_dft)

        # create v1 default data
        if entry_archive.results is None:
            if results is None:
                results = {
                    'material': {
                        'material_id': material_id,
                        'elements': ['H', 'O'],
                        'nelements': 2,
                        'symmetry': {
                            'crystal_system': 'cubic'
                        }
                    },
                    'method': {
                        'simulation': {
                            'program_name': 'VASP',
                            'dft': {
                                'xc_functional_type': 'GGA'
                            }
                        }
                    },
                    'properties': {
                        'n_calculations': 1,
                        'electronic': {
                            'dos_electronic': {
                                'spin_polarized': entry_id.endswith('04')
                            }
                        }
                    }
                }
            if isinstance(results, dict):
                section_results = Results.m_from_dict(results)
            else:
                section_results = results
            assert isinstance(section_results, Results)
            entry_archive.m_add_sub_section(EntryArchive.results, section_results)

        if len(entry_archive.run) == 0:
            entry_archive.m_create(Run)

        if archive is not None:
            entry_archive.m_update(**archive)

        if entry_archive.results.material.material_id is None:
            entry_archive.results.material.material_id = material_id

        if upload_id in self.uploads:
            # Check embargo consistency
            with_embargo = (self.uploads[upload_id]['embargo_length'] > 0)
            assert entry_metadata.with_embargo == with_embargo, 'Inconsistent embargo flags'

        self.archives[entry_id] = entry_archive
        self.entries[entry_id] = entry_metadata
        self.upload_entries.setdefault(entry_metadata.upload_id, []).append(entry_id)

        return entry_archive

    def _next_time_stamp(self):
        '''
        Returns self._time_stamp and ticks up the time stamp with 1 millisecond. This
        utility guarantees that we get unique and increasing time stamps for each entity.
        '''
        self._time_stamp += timedelta(milliseconds=1)
        return self._time_stamp

    def create_structure(
            self,
            id: int, h: int, o: int, extra: List[str], periodicity: int,
            optimade: bool = True, metadata: dict = None):

        ''' Creates a calculation in Elastic and Mongodb with the given properties.

        Does require initialized :func:`elastic_infra` and :func:`mongo_infra`.

        Args:
            meta_info: A legace metainfo env.
            id: A number to create ``test_calc_id_<number>`` ids.
            h: The amount of H atoms
            o: The amount of O atoms
            extra: A list of further atoms
            periodicity: The number of dimensions to repeat the structure in
            optimade: A boolean. Iff true the entry will have optimade metadata. Default is True.
            metadata: Additional (user) metadata.
        '''
        test_vector = [0, 0, 0]
        atom_labels = ['H' for i in range(0, h)] + ['O' for i in range(0, o)] + extra

        archive = EntryArchive()
        run = archive.m_create(Run)
        run.m_create(Program, name='VASP')
        run.m_create(System).m_create(
            Atoms,
            labels=atom_labels,
            positions=[test_vector for i in range(0, len(atom_labels))],
            lattice_vectors=[test_vector, test_vector, test_vector],
            periodic=[True for _ in range(0, periodicity)] + [False for _ in range(periodicity, 3)])

        run_normalize(archive)
        entry_metadata = archive.metadata
        entry_metadata.domain = 'dft'
        entry_metadata.apply_domain_metadata(archive)

        if not optimade:
            entry_metadata.dft.optimade = None

        if metadata is not None:
            kwargs = metadata
        else:
            kwargs = {}

        self.create_entry(
            entry_archive=archive,
            domain='dft', calc_id='test_calc_id_%d' % id, upload_id='test_upload',
            published=True, processed=True, with_embargo=False, **kwargs)


def create_template_upload_file(
        tmp, mainfiles: Union[str, List[str]] = None, auxfiles: int = 4,
        directory: str = 'examples_template', name: str = 'examples_template.zip',
        more_files: Union[str, List[str]] = None):

    '''
    Creates a temporary upload.zip file based on template.json (for the artificial test
    parser) that can be used for test processings.
    '''

    if mainfiles is None:
        mainfiles = 'tests/data/proc/templates/template.json'

    if isinstance(mainfiles, str):
        mainfiles = [mainfiles]

    if more_files is None:
        more_files = []

    if isinstance(more_files, str):
        more_files = [more_files]

    upload_path = os.path.join(tmp, name)
    with zipfile.ZipFile(upload_path, 'w') as zf:
        for i in range(0, auxfiles):
            with zf.open(f'{directory}/{i}.aux', 'w') as f:
                f.write(b'content')
            for mainfile in mainfiles:
                zf.write(mainfile, f'{directory}/{os.path.basename(mainfile)}')

        for additional_file in more_files:
            zf.write(additional_file, f'{directory}/{os.path.basename(additional_file)}')

    return upload_path
