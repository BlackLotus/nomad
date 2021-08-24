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
Contains classes and functions to create and maintain file structures
for uploads, and some generic file utilities.

There are two different structures for uploads in two different states: *staging* and *public*.
Possible operations on uploads differ based on this state. Staging is used for
processing, heavily editing, creating hashes, etc. Public is supposed to be a
almost readonly (beside metadata) storage.

.. code-block:: sh

    fs/staging/<upload>/raw/**
                       /archive/<calc>.json
    fs/public/<upload>/raw-public.plain.zip
                      /raw-restricted.plain.zip
                      /archive-public.json.zip
                      /archive-restricted.json.zip

There is an implicit relationship between files, based on them being in the same
directory. Each directory with at least one *mainfile* is a *calculation directory*
and all the files are *aux* files to that *mainfile*. This is independent of the
respective files actually contributing data or not. A *calculation directory* might
contain multiple *mainfile*. E.g., user simulated multiple states of the same system, have
one calculation based on the other, etc. In this case the other *mainfile* is an *aux*
file to the original *mainfile* and vice versa.

Published files are kept in pairs of public and restricted files. Here the multiple *mainfiles*
per directory provides a dilemma. If on *mainfile* is restricted, all its *aux* files
should be restricted too. But if one of the *aux* files is actually a *mainfile* it
might be published!

There are multiple ways to solve this. Due to the rarity of the case, we take the
most simple solution: if one file is public, all files are made public, execpt those
being other mainfiles. Therefore, the aux files of a restricted calc might become public!
'''

from abc import ABCMeta
import sys
from typing import IO, Dict, Iterable, Iterator, Callable, List, Tuple, Any, NamedTuple
from pydantic import BaseModel
from datetime import datetime
import os.path
import os
import shutil
import tarfile
import zipstream
import hashlib
import io
import json
import magic

from nomad import config, utils, datamodel
from nomad.archive import write_archive, read_archive, ArchiveReader

# TODO this should become obsolete, once we are going beyong python 3.6. For now
# python 3.6's zipfile does not allow to seek/tell within a file-like opened from a
# file in a zipfile.
if sys.version_info >= (3, 7):
    import zipfile
else:
    import zipfile37 as zipfile

zip_file_extensions = ('.zip',)
tar_file_extensions = ('.tgz', '.gz', '.tar.gz', '.tar.bz2', '.tar')


def always_restricted(path: str):
    '''
    Used to put general restrictions on files, e.g. due to licensing issues. Will be
    called during packing and while accessing public files.
    '''
    basename = os.path.basename(path)
    if basename.startswith('POTCAR') and not basename.endswith('.stripped'):
        return True


def copytree(src, dst):
    '''
    A close on ``shutils.copytree`` that does not try to copy the stats on all files.
    This is unecessary for our usecase and also causes permission denies for unknown
    reasons.
    '''
    os.makedirs(dst, exist_ok=False)

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d)
        else:
            shutil.copyfile(s, d)


def create_tmp_dir(prefix: str) -> str:
    '''
    Creates a temporary directory in the directory specified by `config.fs.tmp`. The name
    of the directory will first be set to `prefix`, but if that name is already taken, a
    suffix will be added to ensure a completely clean, new directory is created. If prefix
    contains a '/', it will be replaced with '_', to ensure the validity of the path.
    The full path to the created directory is returned.
    '''
    assert prefix
    prefix = prefix.replace(os.path.sep, '_')
    assert is_safe_basename(prefix)
    for index in range(1, 100):
        dir_name = prefix if index == 1 else f'{prefix}_{index}'
        path = os.path.join(config.fs.tmp, dir_name)
        try:
            os.makedirs(path)
            return path
        except FileExistsError:
            pass  # Try again with different suffix
    raise RuntimeError('Could not create temporary directory - too many directories with same prefix?')


def is_safe_basename(basename: str) -> bool:
    '''
    Checks if `basename` is a *safe* base name (file/folder name). We consider it safe if
    it is not empty, does not contain any '/', and is not equal to '.' or '..'
    '''
    if not basename or '/' in basename or basename == '.' or basename == '..':
        return False
    return True


def is_safe_relative_path(path: str) -> bool:
    '''
    Checks if path is a *safe* relative path. We consider it safe if it does not start with
    '/' or use '.' or '..' elements (which could be open for security leaks if allowed).
    It may end with a single '/', indicating that a folder is referred. For referring to
    the base folder, the empty string should be used (not '.' etc).
    '''
    if type(path) != str:
        return False
    if path == '':
        return True
    if path.startswith('/') or '//' in path or '\n' in path:
        return False
    for element in path.split('/'):
        if element == '.' or element == '..':
            return False
    return True


class PathObject:
    '''
    Object storage-like abstraction for paths in general.
    Attributes:
        os_path: The full os path of the object.
    '''
    def __init__(self, os_path: str):
        self.os_path = os_path

    def delete(self) -> None:
        if os.path.isfile(self.os_path):
            os.remove(self.os_path)
        else:
            shutil.rmtree(self.os_path)

    def exists(self) -> bool:
        return os.path.exists(self.os_path)

    @property
    def size(self) -> int:
        ''' The os determined file size. '''
        return os.stat(self.os_path).st_size

    def __repr__(self) -> str:
        return self.os_path


class DirectoryObject(PathObject):
    '''
    Object storage-like abstraction for directories.
    '''
    def __init__(self, os_path: str, create: bool = False):
        self.os_path = os_path
        if create and not os.path.isdir(self.os_path):
            os.makedirs(self.os_path)

    def join_dir(self, path, create: bool = False) -> 'DirectoryObject':
        return DirectoryObject(os.path.join(self.os_path, path), create)

    def join_file(self, path, create_dir: bool = False) -> PathObject:
        if create_dir:
            dirname = os.path.dirname(path)
            if dirname:
                dir_os_path = os.path.join(self.os_path, dirname)
                if not os.path.exists(dir_os_path):
                    os.makedirs(dir_os_path)
        return PathObject(os.path.join(self.os_path, path))

    def exists(self) -> bool:
        return os.path.isdir(self.os_path)


class Restricted(Exception):
    pass


class RawPathInfo(NamedTuple):
    '''
    Stores basic info about a file or folder located at a specific raw path.
    '''
    path: str
    is_file: bool
    size: int
    access: str


class StreamedFile(BaseModel):
    '''
    Convenience class for representing a streamed file, together with information about
    file size and an associated path.
    '''
    f: Any
    path: str
    size: int


class FileSource(metaclass=ABCMeta):
    '''
    An abstract class which represents a generic "file source", from which some number of files
    can be retrieved. There are several different ways to create a file source, see subclasses.
    The files in the source are associated with paths and have known sizes.
    '''
    def to_streamed_files(self) -> Iterable[StreamedFile]:
        ''' Retrieves the files in the source as :class:`StreamedFile` objects. '''
        raise NotImplementedError()

    def to_zipstream(self) -> Iterator[bytes]:
        ''' Returns a zip stream with the files from this FileSource. '''
        return create_zipstream(self.to_streamed_files())

    def to_zipfile(self, path, overwrite: bool = False):
        '''
        Generates a zip file from the files in this FileSource and stores it to disk. The
        zipfile content is created by calling :func:`to_zipstream`.
        '''
        assert not os.path.isdir(path), 'Exporting to zip file requires a file path, not directory.'
        assert overwrite or not os.path.exists(path), '`path` already exists. Use `overwrite` to overwrite.'
        with open(path, 'wb') as f:
            for chunk in self.to_zipstream():
                f.write(chunk)

    def to_disk(self, destination_dir: str, move_files: bool = False, overwrite: bool = False):
        '''
        Writes the files from this FileSource to disk, uncompressed. The default implementation
        makes use of :func:`to_streamed_files`. The `destination_dir` should be a directory
        (it will be created if it does not exist). The `move_files` argument instructs
        the method to move the source files if possible.
        '''
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        assert os.path.isdir(destination_dir), '`destination_dir` is not a directory'
        for streamed_file in self.to_streamed_files():
            assert is_safe_relative_path(streamed_file.path), 'Unsafe relative path encountered'
            os_path = os.path.join(destination_dir, streamed_file.path)
            dir_path = os.path.dirname(os_path)
            if os.path.exists(os_path):
                assert overwrite, 'Target already exists and `overwrite` is False'
                PathObject(os_path).delete()
            os.makedirs(dir_path, exist_ok=True)
            with open(os_path, 'wb') as output_file:
                for chunk in streamed_file.f:
                    output_file.write(chunk)

    def close(self):
        ''' Perform "closing" of the source, if applicable. '''
        pass


class BrowsableFileSource(FileSource, metaclass=ABCMeta):
    '''
    A :class:`FileSource` which can be "browsed", like a folder on disk or a zip archive.
    '''
    def open(self, path, mode='rb') -> IO:
        ''' Opens a file by the specified path. '''
        raise NotImplementedError()

    def directory_list(self, path: str) -> List[str]:
        '''
        Returns a list of directory contents, located in the directory denoted by `path`
        in this file source.
        '''
        raise NotImplementedError()

    def sub_source(self, path: str) -> 'BrowsableFileSource':
        '''
        Creates a new instance of :class:`BrowsableFileSource` which just contains the
        files located under the specified path.
        '''
        raise NotImplementedError()


class StreamedFileSource(FileSource):
    '''
    A :class:`FileSource` created from a single :class:`StreamedFile`.
    '''
    def __init__(self, streamed_file: StreamedFile):
        self.streamed_file = streamed_file

    def to_streamed_files(self) -> Iterable[StreamedFile]:
        yield self.streamed_file


class DiskFileSource(BrowsableFileSource):
    '''
    A :class:`FileSource` corresponding to a single file or a folder on disk. The object
    is identified by a `base_path` and a `relative path`. The `base_path` should be a folder,
    the `relative_path` is optional, and used for selecting only a specific file or folder
    located under `base_folder`. The paths of the files retrieved from this source are given
    relative to the `base_path`.
    '''
    def __init__(self, base_path: str, relative_path: str = None):
        assert os.path.isdir(base_path)
        if relative_path:
            assert is_safe_relative_path(relative_path), 'Unsafe relative_path received'
            self.full_path = os.path.join(base_path, relative_path)
            assert os.path.exists(self.full_path)
        else:
            self.full_path = base_path
        self.base_path = base_path
        self.relative_path = relative_path

    def to_streamed_files(self) -> Iterable[StreamedFile]:
        if os.path.isfile(self.full_path):
            # Single file
            yield StreamedFile(
                path=self.relative_path,
                f=open(self.full_path, 'rb'),
                size=os.stat(self.full_path).st_size)
        else:
            # Directory - crawl it and its subfolders for files
            for dirpath, __, filenames in os.walk(self.full_path):
                for filename in filenames:
                    sub_full_path = os.path.join(dirpath, filename)
                    sub_relative_path = os.path.relpath(sub_full_path, self.base_path)
                    yield StreamedFile(
                        path=sub_relative_path,
                        f=open(sub_full_path, 'rb'),
                        size=os.stat(sub_full_path).st_size)

    def to_disk(self, destination_dir: str, move_files: bool = False, overwrite: bool = False):
        if self.relative_path:
            destination_path = os.path.join(destination_dir, self.relative_path)
        else:
            destination_path = destination_dir
        destination_parent = os.path.dirname(destination_path)
        os.makedirs(destination_parent, exist_ok=True)
        if os.path.exists(destination_path):
            assert overwrite, f'Target {destination_path} already exists and `overwrite` is False'
            PathObject(destination_path).delete()
        # All looks good. Copy or move the source to the destination
        if move_files:
            shutil.move(self.full_path, destination_path)
        else:
            if os.path.isfile(self.full_path):
                shutil.copyfile(self.full_path, destination_path)
            else:
                copytree(self.full_path, destination_path)

    def open(self, path, mode='rb') -> IO:
        assert is_safe_relative_path(path)
        return open(os.path.join(self.base_path, path), mode)

    def directory_list(self, path: str) -> List[str]:
        assert is_safe_relative_path(path)
        sub_path = os.path.join(self.base_path, path)
        return os.listdir(sub_path)

    def sub_source(self, path: str) -> 'DiskFileSource':
        assert is_safe_relative_path(path)
        return DiskFileSource(self.base_path, path)


class ZipFileSource(BrowsableFileSource):
    '''
    Allows us to "wrap" a :class:`zipfile.ZipFile` object and use it as a :class:`BrowsableFileSource`,
    i.e. it denotes a resource (single file or folder) stored in a ZipFile.
    '''
    def __init__(self, zip_file: zipfile.ZipFile, sub_path: str = ''):
        assert is_safe_relative_path(sub_path)
        self.zip_file = zip_file
        self.sub_path = sub_path
        self._namelist: List[str] = zip_file.namelist()

    def to_streamed_files(self) -> Iterable[StreamedFile]:
        path_prefix = '' if not self.sub_path else self.sub_path + os.path.sep
        for path in self._namelist:
            if path == self.sub_path or (path.startswith(path_prefix) and not path.endswith(os.path.sep)):
                yield StreamedFile(
                    path=path,
                    f=self.zip_file.open(path, 'r'),
                    size=self.zip_file.getinfo(path).file_size)

    def open(self, path, mode='rb') -> IO:
        assert 'r' in mode, 'Mode must be a read mode'
        for c in mode:
            assert c in ('r', 'b', 't'), f'Invalid mode for open command: {mode}'
        f = self.zip_file.open(path, 'r')
        if 't' in mode:
            return io.TextIOWrapper(f)
        return f

    def directory_list(self, path: str) -> List[str]:
        path_prefix = '' if not path else path + os.path.sep
        found = set()
        for path2 in self._namelist:
            if path2.startswith(path_prefix):
                found.add(path2.split(os.path.sep)[0])
        return sorted(found)

    def sub_source(self, path: str) -> 'ZipFileSource':
        assert is_safe_relative_path(path), 'Unsafe path provided'
        if self.sub_path:
            assert path.startswith(self.sub_path + os.path.sep), 'Provided `path` is not a sub path.'
        return ZipFileSource(self.zip_file, path)

    def close(self):
        self.zip_file.close()


class CombinedFileSource(FileSource):
    '''
    Class for defining a :class:`FileSource` by combining multiple "subsources" into one.
    New sources are added using :func:`add_file_source`.
    '''
    def __init__(self):
        self.sources = []

    def add_file_source(self, file_source: FileSource):
        assert isinstance(file_source, FileSource)
        self.sources.append(file_source)

    def to_streamed_files(self) -> Iterable[StreamedFile]:
        for file_source in self.sources:
            for streamed_file in file_source.to_streamed_files():
                yield streamed_file

    def to_disk(self, destination_dir: str, move_files: bool = False, overwrite: bool = False):
        for file_source in self.sources:
            file_source.to_disk(destination_dir, move_files, overwrite)


class StandardJSONEncoder(json.JSONEncoder):
    """ Our standard JSONEncoder with support for marshalling of datetime objects """
    def default(self, obj):  # pylint: disable=E0202
        if isinstance(obj, datetime):
            return {'$datetime': obj.timestamp()}
        return json.JSONEncoder.default(self, obj)


class StandardJSONDecoder(json.JSONDecoder):
    """ Our standard JSONDecoder, with support for marshalling of datetime objects """
    def __init__(self, *args, **kargs):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object, *args, **kargs)

    def dict_to_object(self, d):
        v = d.get('$datetime')
        if v is not None:
            return datetime.fromtimestamp(v)
        return d


def json_to_streamed_file(json_dict: Dict[str, Any], path: str) -> StreamedFile:
    ''' Converts a json dictionary structure to a :class:`StreamedFile`. '''
    json_bytes = json.dumps(json_dict, indent=2, cls=StandardJSONEncoder).encode()
    return StreamedFile(
        path=path,
        f=io.BytesIO(json_bytes),
        size=len(json_bytes))


def create_zipstream_content(streamed_files: Iterable[StreamedFile]) -> Iterable[Dict]:
    '''
    Generator which "casts" a sequence of StreamedFiles to a sequence of dictionaries, of
    the form which is required by the `zipstream` library, i.e. dictionaries with keys
    `arcname`, `iterable` and `buffer_size`. Useful for generating zipstreams.
    '''
    for streamed_file in streamed_files:

        def content_generator():
            while True:
                data = streamed_file.f.read(1024 * 64)
                if not data:
                    break
                yield data

        yield dict(
            arcname=streamed_file.path,
            iterable=content_generator(),
            buffer_size=streamed_file.size)


def create_zipstream(
        streamed_files: Iterable[StreamedFile],
        compress: bool = False) -> Iterator[bytes]:
    '''
    Creates a zip stream, i.e. a streamed zip file.
    '''
    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    zip_stream = zipstream.ZipFile(mode='w', compression=compression, allowZip64=True)
    zip_stream.paths_to_write = create_zipstream_content(streamed_files)

    return iter(zip_stream)


class UploadFiles(DirectoryObject, metaclass=ABCMeta):
    ''' Abstract base class for upload files. '''
    def __init__(
            self, upload_id: str, is_authorized: Callable[[], bool] = lambda: False,
            create: bool = False) -> None:
        self.logger = utils.get_logger(__name__, upload_id=upload_id)

        super().__init__(os_path=self.base_folder_for(upload_id), create=create)

        if not create and not self.exists():
            raise KeyError(upload_id)

        self.upload_id = upload_id
        self._is_authorized = is_authorized

    @classmethod
    def file_area(cls):
        '''
        Full path to where the upload files of this class are stored (i.e. either
        staging or public file area).
        '''
        raise NotImplementedError()

    @classmethod
    def base_folder_for(cls, upload_id: str) -> str:
        '''
        Full path to the base folder for the upload files (of this class) for the
        specified upload_id.
        '''
        os_path = cls.file_area()
        if config.fs.prefix_size:
            os_path = os.path.join(os_path, upload_id[:config.fs.prefix_size])
        os_path = os.path.join(os_path, upload_id)
        return os_path

    @classmethod
    def exists_for(cls, upload_id: str) -> bool:
        '''
        If an UploadFiles object (of this class) has been created for this upload_id.
        '''
        return os.path.exists(cls.base_folder_for(upload_id))

    def to_staging_upload_files(self, create: bool = False, include_archive: bool = False) -> 'StagingUploadFiles':
        ''' Casts to or creates corresponding staging upload files or returns None. '''
        raise NotImplementedError()

    @staticmethod
    def get(upload_id: str, *args, **kwargs) -> 'UploadFiles':
        if StagingUploadFiles.exists_for(upload_id):
            return StagingUploadFiles(upload_id, *args, **kwargs)
        elif PublicUploadFiles.exists_for(upload_id):
            return PublicUploadFiles(upload_id, *args, **kwargs)
        else:
            return None

    def is_empty(self) -> bool:
        ''' If this upload has no content yet. '''
        raise NotImplementedError()

    def raw_path_exists(self, path: str) -> bool:
        '''
        Returns True if the specified path is a valid raw path (either file or directory)
        '''
        raise NotImplementedError()

    def raw_path_is_file(self, path: str) -> bool:
        '''
        Returns True if the specified path points to a file (rather than a directory).
        '''
        raise NotImplementedError()

    def raw_directory_list(
            self, path: str = '', recursive=False, files_only=False, path_prefix=None) -> Iterable[RawPathInfo]:
        '''
        Returns an iterable of RawPathInfo, one for each element (file or folder) in
        the directory specified by `path`. If `recursive` is set to True, subdirectories are
        also crawled. If `files_only` is set, only the file objects found are returned.
        If path is not a valid directory, the result will be empty. Selecting empty string
        as path (which is the default value) gives the content of the whole raw directory.
        The `path_prefix` argument can be used to filter out elements where the path starts
        with a specific prefix.
        '''
        raise NotImplementedError()

    def raw_file(self, file_path: str, *args, **kwargs) -> IO:
        '''
        Opens a raw file and returns a file-like object. Additional args, kwargs are
        delegated to the respective `open` call.
        Arguments:
            file_path: The path to the file relative to the upload.
        Raises:
            KeyError: If the file does not exist.
            Restricted: If the file is restricted and upload access evaluated to False.
        '''
        raise NotImplementedError()

    def raw_file_size(self, file_path: str) -> int:
        '''
        Returns:
            The size of the given raw file.
        '''
        raise NotImplementedError()

    def raw_file_mime_type(self, file_path: str) -> str:
        assert self.raw_path_is_file(file_path), 'Provided path does not specify a file, or is invalid.'
        raw_file = self.raw_file(file_path, 'br')
        buffer = raw_file.read(2048)
        mime_type = magic.from_buffer(buffer, mime=True)
        raw_file.close()
        if not mime_type:
            mime_type = 'application/octet-stream'
        return mime_type

    def read_archive(self, calc_id: str, access: str = None) -> ArchiveReader:
        '''
        Returns an :class:`nomad.archive.ArchiveReader` that contains the
        given calc_id. Both restricted and public archive are searched by default.
        The optional ``access`` parameter can be used to limit this lookup to the
        ``public`` or ``restricted`` archive.'''
        raise NotImplementedError()

    def close(self):
        ''' Release possibly held system resources (e.g. file handles). '''
        pass

    def delete(self) -> None:
        shutil.rmtree(self.os_path)
        if config.fs.prefix_size > 0:
            # If using prefix, also remove the parent directory if empty
            parent_directory = os.path.dirname(self.os_path)
            if not os.listdir(parent_directory):
                try:
                    os.rmdir(parent_directory)
                except Exception as e:
                    utils.get_logger(__name__).error(
                        'could not remove empty prefix dir', directory=parent_directory, exc_info=e)

    def files_to_bundle(
            self, bundle_info: Dict[str, Any],
            include_raw_files: bool, include_protected_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        '''
        Returns a :class:`FileSource`, defining the files/folders to be included in an
        upload bundle when *exporting*. Note, the bundle_info.json file is not included,
        only the "regular" files, and only those specified by the arguments to the method.
        '''
        raise NotImplementedError()

    @classmethod
    def files_from_bundle(
            cls, budle_file_source: BrowsableFileSource,
            include_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        '''
        Returns a :class:`FileSource`, defining the files/folders to be included in an
        upload bundle when *importing*. Note, the bundle_info.json file is not included in
        the source, only the "regular" files, and only those specified by the arguments
        to the method.
        '''
        raise NotImplementedError()


class StagingUploadFiles(UploadFiles):
    def __init__(
            self, upload_id: str, is_authorized: Callable[[], bool] = lambda: False,
            create: bool = False) -> None:
        super().__init__(upload_id, is_authorized, create)

        self._raw_dir = self.join_dir('raw', create)
        self._archive_dir = self.join_dir('archive', create)
        self._frozen_file = self.join_file('.frozen')

        self._size = 0

    @classmethod
    def file_area(cls):
        return config.fs.staging

    def to_staging_upload_files(self, create: bool = False, include_archive: bool = False) -> 'StagingUploadFiles':
        return self

    @property
    def size(self) -> int:
        return self._size

    def _file(self, path_object: PathObject, *args, **kwargs) -> IO:
        try:
            return open(path_object.os_path, *args, **kwargs)
        except FileNotFoundError:
            raise KeyError(path_object.os_path)
        except IsADirectoryError:
            raise KeyError(path_object.os_path)

    def is_empty(self) -> bool:
        return not os.path.exists(self._raw_dir.os_path) or not os.listdir(self._raw_dir.os_path)

    def raw_path_exists(self, path: str) -> bool:
        if not is_safe_relative_path(path):
            return False
        return os.path.exists(os.path.join(self._raw_dir.os_path, path))

    def raw_path_is_file(self, path: str) -> bool:
        if not is_safe_relative_path(path):
            return False
        return os.path.isfile(os.path.join(self._raw_dir.os_path, path))

    def raw_directory_list(
            self, path: str = '', recursive=False, files_only=False, path_prefix=None) -> Iterable[RawPathInfo]:
        if not is_safe_relative_path(path):
            return
        os_path = os.path.join(self._raw_dir.os_path, path)
        if not os.path.isdir(os_path):
            return
        for element_name in sorted(os.listdir(os_path)):
            element_raw_path = os.path.join(path, element_name)
            element_os_path = os.path.join(os_path, element_name)
            is_file = os.path.isfile(element_os_path)
            if not is_file:
                # Crawl sub directory.
                dir_size = 0
                for sub_path_info in self.raw_directory_list(element_raw_path, True, files_only):
                    if sub_path_info.is_file:
                        dir_size += sub_path_info.size
                    if recursive:
                        if not path_prefix or sub_path_info.path.startswith(path_prefix):
                            yield sub_path_info

            if not files_only or is_file:
                size = os.stat(element_os_path).st_size if is_file else dir_size
                if not path_prefix or element_raw_path.startswith(path_prefix):
                    yield RawPathInfo(
                        path=element_raw_path,
                        is_file=is_file,
                        size=size,
                        access='unpublished')

    def raw_file(self, file_path: str, *args, **kwargs) -> IO:
        assert is_safe_relative_path(file_path)
        if not self._is_authorized():
            raise Restricted
        return self._file(self.raw_file_object(file_path), *args, **kwargs)

    def raw_file_size(self, file_path: str) -> int:
        assert is_safe_relative_path(file_path)
        if not self._is_authorized():
            raise Restricted
        return self.raw_file_object(file_path).size

    def raw_file_object(self, file_path: str) -> PathObject:
        assert is_safe_relative_path(file_path)
        return self._raw_dir.join_file(file_path)

    def write_archive(self, calc_id: str, data: Any) -> int:
        ''' Writes the data as archive file and returns the archive file size. '''
        archive_file_object = self.archive_file_object(calc_id)
        try:
            write_archive(archive_file_object.os_path, 1, data=[(calc_id, data)])
        except Exception as e:
            # in case of failure, remove the possible corrupted archive file
            if archive_file_object.exists():
                archive_file_object.delete()

            raise e

        return self.archive_file_object(calc_id).size

    def read_archive(self, calc_id: str, access: str = None) -> ArchiveReader:
        if not self._is_authorized():
            raise Restricted

        try:
            return read_archive(self.archive_file_object(calc_id).os_path)

        except FileNotFoundError:
            raise KeyError(calc_id)

    def archive_file_object(self, calc_id: str) -> PathObject:
        return self._archive_dir.join_file('%s.%s' % (calc_id, 'msg'))

    def add_rawfiles(
            self, path: str, target_dir: str = '', cleanup_source_file_and_dir: bool = False) -> None:
        '''
        Adds the file or folder specified by `path` to this upload, in the raw directory
        specified by `target_dir`. If `path` denotes a zip or tar archive file, it will
        first be extracted to a temporary directory. The file(s) are *merged* with the
        existing upload files, i.e. new files are added, replacing old files if there
        already exists file(s) by the same names, the rest of the old files are left
        untouched.

        Cleanup
        The method is responsible for trying to clean up temporarily extracted files.
        If `cleanup_source_file_and_dir` is True, the source file (defined by `path`), and
        its parent directory (which we also assume is temporary) are also cleaned up.
        Note: the cleanup steps are always carried out, also if the operation fails.

        Arguments:
            path: OS path to a file or folder to add.
            target_dir: A raw path (i.e. path relative to the raw directory) defining
                where the resource defined by `path` should be put. If `target_dir` is not
                specified, it defaults to the empty string, i.e. the upload's raw dir.
            cleanup_source_file_and_dir: If true, the source file (defined by `path`) and
                its parent folder are included in the cleanup step - i.e. they are always
                deleted. Use when the file is stored temporarily.
        '''
        tmp_dir = None
        try:
            assert not self.is_frozen
            assert os.path.exists(path), f'{path} does not exist'
            assert is_safe_relative_path(target_dir)
            ext = os.path.splitext(path)[1]
            self._size += os.stat(path).st_size

            is_dir = os.path.isdir(path)
            if is_dir:
                is_zipfile = is_tarfile = False
            else:
                is_zipfile = zipfile.is_zipfile(path) or ext in zip_file_extensions
                is_tarfile = tarfile.is_tarfile(path) or ext in tar_file_extensions
                if is_zipfile or is_tarfile:
                    tmp_dir = create_tmp_dir(self.upload_id + '_unzip')
                    if is_zipfile:
                        with zipfile.ZipFile(path) as zf:
                            zf.extractall(tmp_dir)
                    elif is_tarfile:
                        with tarfile.open(path) as tf:
                            tf.extractall(tmp_dir)

            # Determine what to merge
            elements_to_merge: Iterable[Tuple[str, List[str], List[str]]] = []
            if is_dir or is_zipfile or is_tarfile:
                # Directory
                source_dir = path if is_dir else tmp_dir
                elements_to_merge = os.walk(source_dir)
            else:
                # Single file
                source_dir = os.path.dirname(path)
                elements_to_merge = [(source_dir, [], [os.path.basename(path)])]

            # Ensure target_dir exists and is a directory. If one of the elements in the
            # directory chain is a file, it needs to be deleted (the regular os.makedirs
            # doesn't do that).
            target_dir_subpath = self._raw_dir.os_path
            for dir_name in target_dir.split(os.path.sep):
                target_dir_subpath = os.path.join(target_dir_subpath, dir_name)
                if os.path.isfile(target_dir_subpath):
                    os.remove(target_dir_subpath)
                if not os.path.isdir(target_dir_subpath):
                    os.makedirs(target_dir_subpath)

            # Do the merge
            for root, dirs, files in elements_to_merge:
                elements = dirs + files
                os_target_dir = os.path.join(self._raw_dir.os_path, target_dir)
                for element in elements:
                    element_source_path = os.path.join(root, element)
                    element_relative_path = os.path.relpath(element_source_path, source_dir)
                    element_target_path = os.path.join(os_target_dir, element_relative_path)
                    if os.path.islink(element_source_path):
                        continue  # Skip links, could pose security risk
                    if os.path.exists(element_target_path):
                        if not (os.path.isdir(element_source_path) and os.path.isdir(element_target_path)):
                            # Target already exists and needs to be deleted
                            if os.path.isdir(element_target_path):
                                shutil.rmtree(element_target_path)
                            else:
                                os.remove(element_target_path)
                    # Copy or move the element
                    if os.path.isdir(element_source_path):
                        # Directory - just create corresponding directory in the target if needed.
                        if not os.path.exists(element_target_path):
                            os.makedirs(element_target_path)
                    else:
                        # File - copy or move it
                        if cleanup_source_file_and_dir or is_zipfile or is_tarfile:
                            # Move the file
                            shutil.move(element_source_path, element_target_path)
                        else:
                            # Copy the file
                            shutil.copyfile(element_source_path, element_target_path)
        finally:
            # Cleanup
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            if cleanup_source_file_and_dir:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                parent_dir = os.path.dirname(path)
                if os.path.exists(parent_dir):
                    shutil.rmtree(parent_dir)

    def delete_rawfiles(self, path):
        assert is_safe_relative_path(path)
        os_path = os.path.join(self.os_path, 'raw', path)
        assert os.path.exists(os_path)
        if os.path.isfile(os_path):
            os.remove(os_path)
        else:
            shutil.rmtree(os_path)
        if path == '':
            # Special case - deleting everything, i.e. the entire raw folder. Need to recreate.
            os.makedirs(os_path)

    @property
    def is_frozen(self) -> bool:
        ''' Returns True if this upload is already *bagged*. '''
        return self._frozen_file.exists()

    def pack(
            self, entries: Iterable[datamodel.EntryMetadata], create: bool = True,
            include_raw: bool = True, include_archive: bool = True) -> None:
        '''
        Replaces the staging upload data with a public upload record by packing all
        data into files. It is only available if upload *is_bag*.
        This is potentially a long running operation.

        Arguments:
            upload: The upload with all calcs and  calculation metadata of the upload
                used to determine what files to pack and what the embargo situation is.
            create: if the public upload files directory should be created.
            include_raw: determines if the raw data should be packed. True by default.
            include_archive: determines of the archive data should be packed. True by default.
        '''
        self.logger.info('started to pack upload')

        # freeze the upload
        assert not self.is_frozen, "Cannot pack an upload that is packed, or packing."
        with open(self._frozen_file.os_path, 'wt') as f:
            f.write('frozen')

        # Get or create a target dir in the public bucket
        target_dir = DirectoryObject(PublicUploadFiles.base_folder_for(self.upload_id), create=create)

        def create_zipfile(access: str):
            return zipfile.ZipFile(
                PublicUploadFiles._create_raw_file_object(target_dir, access).os_path,
                mode='w')

        def write_msgfile(access: str, size: int, data: Iterable[Tuple[str, Any]]):
            file_object = PublicUploadFiles._create_msg_file_object(target_dir, access)
            write_archive(file_object.os_path, size, data)

        # zip archives
        if include_archive:
            with utils.timer(self.logger, 'packed msgpack archive') as log_data:
                restricted, public = self._pack_archive_files(entries, write_msgfile)
                log_data.update(restricted=restricted, public=public)

        # zip raw files
        if include_raw:
            with utils.timer(self.logger, 'packed raw files'):
                self._pack_raw_files(entries, create_zipfile)

    def _pack_archive_files(self, entries: Iterable[datamodel.EntryMetadata], write_msgfile):
        restricted, public = 0, 0
        for calc in entries:
            if calc.with_embargo:
                restricted += 1
            else:
                public += 1

        def create_iterator(with_embargo: bool):
            for calc in entries:
                if with_embargo == calc.with_embargo:
                    archive_file = self.archive_file_object(calc.calc_id)
                    if archive_file.exists():
                        data = read_archive(archive_file.os_path)[calc.calc_id].to_dict()
                        yield (calc.calc_id, data)
                    else:
                        yield (calc.calc_id, {})

        try:
            write_msgfile('public', public, create_iterator(False))
            write_msgfile('restricted', restricted, create_iterator(True))

        except Exception as e:
            self.logger.error('exception during packing archives', exc_info=e)

        return restricted, public

    def _pack_raw_files(self, entries: Iterable[datamodel.EntryMetadata], create_zipfile):
        raw_public_zip = create_zipfile('public')
        raw_restricted_zip = create_zipfile('restricted')

        try:
            # 1. add all public raw files
            # 1.1 collect all public mainfiles and aux files
            public_files: Dict[str, str] = {}
            for calc in entries:
                if not calc.with_embargo:
                    mainfile = calc.mainfile
                    assert mainfile is not None
                    # mainfile might already have been added due to being a auxfile to another calc
                    if mainfile not in public_files:
                        for filepath in self.calc_files(mainfile, with_cutoff=False):
                            if not always_restricted(filepath):
                                public_files[filepath] = None
            # 1.2 remove the non public mainfiles that have been added as auxfiles of public mainfiles
            for calc in entries:
                if calc.with_embargo:
                    mainfile = calc.mainfile
                    assert mainfile is not None
                    if mainfile in public_files:
                        del(public_files[mainfile])
            # 1.3 zip all remaining public
            for filepath in public_files.keys():
                raw_public_zip.write(self._raw_dir.join_file(filepath).os_path, filepath)

            # 2. everything else becomes restricted
            for path_info in self.raw_directory_list(recursive=True, files_only=True):
                filepath = path_info.path
                if filepath not in public_files:
                    raw_restricted_zip.write(self._raw_dir.join_file(filepath).os_path, filepath)

        except Exception as e:
            self.logger.error('exception during packing raw files', exc_info=e)

        finally:
            raw_restricted_zip.close()
            raw_public_zip.close()

    def calc_files(self, mainfile: str, with_mainfile: bool = True, with_cutoff: bool = True) -> Iterable[str]:
        '''
        Returns all the auxfiles and mainfile for a given mainfile. This implements
        nomad's logic about what is part of a calculation and what not. The mainfile
        is first entry, the rest is sorted.
        Arguments:
            mainfile: The mainfile relative to upload
            with_mainfile: Do include the mainfile, default is True
        '''
        mainfile_object = self._raw_dir.join_file(mainfile)
        if not mainfile_object.exists():
            raise KeyError(mainfile)

        mainfile_basename = os.path.basename(mainfile)
        calc_dir = os.path.dirname(mainfile_object.os_path)
        calc_relative_dir = calc_dir[len(self._raw_dir.os_path) + 1:]

        file_count = 0
        aux_files: List[str] = []
        for filename in os.listdir(calc_dir):
            if filename != mainfile_basename and os.path.isfile(os.path.join(calc_dir, filename)):
                aux_files.append(os.path.join(calc_relative_dir, filename))
                file_count += 1

            if with_cutoff and file_count > config.auxfile_cutoff:
                # If there are two many of them, its probably just a directory with lots of
                # calculations. In this case it does not make any sense to provide thousands of
                # aux files.
                break

        aux_files = sorted(aux_files)

        if with_mainfile:
            return [mainfile] + aux_files
        else:
            return aux_files

    def calc_hash(self, mainfile: str) -> str:
        '''
        Calculates a hash for the given calc based on file contents and aux file contents.
        Arguments:
            mainfile: The mainfile path relative to the upload that identifies the calc in the folder structure.
        Returns:
            The calculated hash
        Raises:
            KeyError: If the mainfile does not exist.
        '''
        hash = hashlib.sha512()
        for filepath in self.calc_files(mainfile):
            with open(self._raw_dir.join_file(filepath).os_path, 'rb') as f:
                for data in iter(lambda: f.read(65536), b''):
                    hash.update(data)

        return utils.make_websave(hash)

    def files_to_bundle(
            self, bundle_info: Dict[str, Any],
            include_raw_files: bool, include_protected_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        # Files to export for staging uploads.
        if include_raw_files and not include_protected_raw_files:
            assert False, 'Excluding protected files not supported for uploads in staging.'
        rv = CombinedFileSource()
        rv.add_file_source(StreamedFileSource(json_to_streamed_file(bundle_info, 'bundle_info.json')))
        if include_raw_files and include_protected_raw_files:
            rv.add_file_source(DiskFileSource(self.os_path, 'raw'))
        if include_archive_files:
            rv.add_file_source(DiskFileSource(self.os_path, 'archive'))
        return rv

    @classmethod
    def files_from_bundle(
            cls, budle_file_source: BrowsableFileSource,
            include_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        # Files to import for a staging upload
        rv = CombinedFileSource()
        if include_raw_files:
            rv.add_file_source(budle_file_source.sub_source('raw'))
        if include_archive_files:
            rv.add_file_source(budle_file_source.sub_source('archive'))
        return rv


class PublicUploadFiles(UploadFiles):

    def __init__(
            self, upload_id: str, is_authorized: Callable[[], bool] = lambda: False,
            create: bool = False):
        super().__init__(upload_id, is_authorized, create)
        self._directories: Dict[str, Dict[str, RawPathInfo]] = None
        self._raw_zip_files: Dict[str, zipfile.ZipFile] = {}
        self._archive_msg_files: Dict[str, ArchiveReader] = {}

    @classmethod
    def file_area(cls):
        return config.fs.public

    def close(self):
        for f in self._raw_zip_files.values():
            f.close()

        for f in self._archive_msg_files.values():
            f.close()

    @staticmethod
    def _create_raw_file_object(dir: DirectoryObject, access: str, suffix: str = '') -> PathObject:
        return dir.join_file(f'raw-{access}{suffix}.plain.zip')

    def raw_file_object(self, access: str, **kwargs) -> PathObject:
        return PublicUploadFiles._create_raw_file_object(self, access, **kwargs)

    def _open_raw_file(self, access: str) -> zipfile.ZipFile:
        if access in self._raw_zip_files:
            return self._raw_zip_files[access]

        zip_path = self.raw_file_object(access).os_path
        f = zipfile.ZipFile(zip_path)
        self._raw_zip_files[access] = f

        return f

    @staticmethod
    def _create_msg_file_object(dir: DirectoryObject, access: str, suffix: str = '') -> PathObject:
        if config.fs.archive_version_suffix:
            return dir.join_file(
                f'archive-{access}{suffix}-{config.fs.archive_version_suffix}.msg.msg')

        return dir.join_file(f'archive-{access}{suffix}.msg.msg')

    def msg_file_object(self, access: str, **kwargs) -> PathObject:
        return PublicUploadFiles._create_msg_file_object(self, access, **kwargs)

    def _open_msg_file(self, access: str) -> ArchiveReader:
        if access in self._archive_msg_files:
            archive = self._archive_msg_files[access]
            if not archive.is_closed():
                return archive

        msg_object = self.msg_file_object(access)

        if not msg_object.exists():
            raise FileNotFoundError()

        archive = read_archive(msg_object.os_path)
        assert archive is not None
        self._archive_msg_files[access] = archive

        return archive

    def to_staging_upload_files(self, create: bool = False, include_archive: bool = False) -> 'StagingUploadFiles':
        exists = False
        try:
            staging_upload_files = StagingUploadFiles(self.upload_id, is_authorized=lambda: True)
            exists = True
        except KeyError:
            if not create:
                return None

            staging_upload_files = StagingUploadFiles(self.upload_id, create=True, is_authorized=lambda: True)
            # Extract files
            for access in ['public', 'restricted']:
                raw_file_zip = self.raw_file_object(access)
                if raw_file_zip.exists():
                    staging_upload_files.add_rawfiles(raw_file_zip.os_path)

                if include_archive:
                    with self._open_msg_file(access) as archive:
                        for calc_id, data in archive.items():
                            calc_id = calc_id.strip()
                            staging_upload_files.write_archive(calc_id, data.to_dict())

        if exists and create:
            raise FileExistsError('Staging upload does already exist')

        return staging_upload_files

    def add_metadata_file(self, metadata: dict):
        zip_path = self.raw_file_object('public').os_path
        with zipfile.ZipFile(zip_path, 'a') as zf:
            with zf.open('nomad.json', 'w') as f:
                f.write(json.dumps(metadata).encode())

    def _parse_content(self):
        '''
        Parses the content of files and folders and caches it in self._directories for
        faster future access.
        '''
        if self._directories is None:
            self._directories = dict()
            self._directories[''] = {}  # Root folder
            directory_sizes: Dict[str, int] = {}
            # Add file RawPathInfo objects and calculate directory sizes
            for access in ['public', 'restricted']:
                try:
                    zf = self._open_raw_file(access)
                    for path in zf.namelist():
                        file_name = os.path.basename(path)
                        directory_path = os.path.dirname(path)
                        size = zf.getinfo(path).file_size if file_name else 0

                        # Ensure that all parent directories are added
                        sub_path = ''
                        for directory in directory_path.split(os.path.sep):
                            sub_path_next = os.path.join(sub_path, directory)
                            if sub_path_next not in self._directories:
                                self._directories[sub_path_next] = {}
                            directory_sizes.setdefault(sub_path_next, 0)
                            directory_sizes[sub_path_next] += size
                            sub_path = sub_path_next

                        if file_name:
                            directory_content = self._directories[directory_path]
                            directory_content[file_name] = RawPathInfo(
                                path=path,
                                is_file=True,
                                size=size,
                                access=access)
                except FileNotFoundError:
                    pass
            # Add directories with the calculated sizes.
            for path, size in directory_sizes.items():
                basename = os.path.basename(path)
                directory_path = os.path.dirname(path)
                self._directories[directory_path][basename] = RawPathInfo(
                    path=path, is_file=False, size=size, access='Public')

    def is_empty(self) -> bool:
        self._parse_content()
        return not self._directories.get('')

    def raw_path_exists(self, path: str) -> bool:
        if not is_safe_relative_path(path):
            return False
        self._parse_content()
        explicit_directory_path = path.endswith(os.path.sep)
        path = path.rstrip(os.path.sep)
        base_name = os.path.basename(path)
        directory_path = os.path.dirname(path)
        directory_content = self._directories.get(directory_path)
        if directory_content is not None:
            if not base_name:
                return True
            if base_name in directory_content:
                path_info = directory_content[base_name]
                if path_info.access == 'public' or self._is_authorized():
                    if explicit_directory_path and path_info.is_file:
                        return False
                    return True
        return False

    def raw_path_is_file(self, path: str) -> bool:
        if not is_safe_relative_path(path):
            return False
        self._parse_content()
        base_name = os.path.basename(path)
        directory_path = os.path.dirname(path)
        if not base_name:
            return False  # Requested path is an explicit directory path
        directory_content = self._directories.get(directory_path)
        if directory_content and base_name in directory_content:
            path_info = directory_content[base_name]
            if path_info.access == 'public' or self._is_authorized():
                return path_info.is_file
        return False

    def raw_directory_list(
            self, path: str = '', recursive=False, files_only=False, path_prefix=None) -> Iterable[RawPathInfo]:
        if not is_safe_relative_path(path):
            return
        self._parse_content()
        path = path.rstrip(os.path.sep)
        directory_content = self._directories.get(path)
        if directory_content is not None:
            for __, path_info in sorted(directory_content.items()):
                if not files_only or path_info.is_file:
                    if not path_prefix or path_info.path.startswith(path_prefix):
                        yield path_info
                if recursive and not path_info.is_file:
                    for sub_path_info in self.raw_directory_list(path_info.path, recursive, files_only):
                        if not path_prefix or sub_path_info.path.startswith(path_prefix):
                            yield sub_path_info

    @property
    def public_raw_data_file(self):
        return self.raw_file_object('public').os_path

    def raw_file(self, file_path: str, *args, **kwargs) -> IO:
        assert is_safe_relative_path(file_path)
        mode = kwargs.get('mode') if len(args) == 0 else args[0]
        if 'mode' in kwargs:
            del(kwargs['mode'])
        mode = mode if mode else 'rb'

        for access in ['public', 'restricted']:
            try:
                zf = self._open_raw_file(access)
                f = zf.open(file_path, 'r', **kwargs)

                if (access == 'restricted' or always_restricted(file_path)) and not self._is_authorized():
                    raise Restricted

                if 't' in mode:
                    return io.TextIOWrapper(f)
                else:
                    return f
            except FileNotFoundError:
                pass
            except IsADirectoryError:
                pass
            except KeyError:
                pass

        raise KeyError(file_path)

    def raw_file_size(self, file_path: str) -> int:
        assert is_safe_relative_path(file_path)
        for access in ['public', 'restricted']:
            try:
                zf = self._open_raw_file(access)
                info = zf.getinfo(file_path)
                if (access == 'restricted' or always_restricted(file_path)) and not self._is_authorized():
                    raise Restricted

                return info.file_size
            except FileNotFoundError:
                pass
            except KeyError:
                pass

        raise KeyError(file_path)

    def read_archive(self, calc_id: str, access: str = None) -> Any:
        if access is not None:
            accesses = [access]
        else:
            accesses = ['public', 'restricted']

        for access in accesses:
            try:
                archive = self._open_msg_file(access)
                if calc_id in archive:
                    if access == 'restricted' and not self._is_authorized():
                        raise Restricted

                    return archive
            except FileNotFoundError:
                pass

        raise KeyError(calc_id)

    def re_pack(
            self, entries: Iterable[datamodel.EntryMetadata], include_raw: bool = True,
            include_archive: bool = True) -> None:
        '''
        Replaces the existing public/restricted data file pairs with new ones, based
        on current restricted information in the metadata. Should be used after updating
        the restrictions on calculations. This is potentially a long running operation.
        '''
        # compute a list of files to repack
        files = []

        for access in ['public', 'restricted']:
            if include_archive:
                files.append((
                    self.msg_file_object(access, suffix='repacked'),
                    self.msg_file_object(access)))
            if include_raw:
                files.append((
                    self.raw_file_object(access, suffix='repacked'),
                    self.raw_file_object(access)))

        # check if there already is a running repack
        for repacked_file, _ in files:
            if repacked_file.exists():
                raise FileExistsError('Repacked files already exist')

        # create staging files
        staging_upload = self.to_staging_upload_files(create=True, include_archive=True)

        def create_zipfile(access: str) -> zipfile.ZipFile:
            file = self.raw_file_object(access, suffix='repacked')
            return zipfile.ZipFile(file.os_path, mode='w')

        def write_msgfile(access: str, size: int, data: Iterable[Tuple[str, Any]]):
            file = self.msg_file_object(access, suffix='repacked')
            write_archive(file.os_path, size, data)

        # perform the repacking
        try:
            if include_archive:
                # staging_upload._pack_archive_files(entries, create_zipfile)
                staging_upload._pack_archive_files(entries, write_msgfile)
            if include_raw:
                staging_upload._pack_raw_files(entries, create_zipfile)
        finally:
            staging_upload.delete()

        # replace the original files with the repacked ones
        for repacked_file, public_file in files:
            shutil.move(
                repacked_file.os_path,
                public_file.os_path)

    def files_to_bundle(
            self, bundle_info: Dict[str, Any],
            include_raw_files: bool, include_protected_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        # Defines files for upload bundles of published uploads.
        if include_raw_files and not include_protected_raw_files:
            # TODO: Probably need to support this in the future
            raise NotImplementedError('Excluding protected files not yet supported')
        rv = CombinedFileSource()
        rv.add_file_source(StreamedFileSource(json_to_streamed_file(bundle_info, 'bundle_info.json')))
        for filename in os.listdir(self.os_path):
            if filename.startswith('raw-') and include_raw_files:
                rv.add_file_source(DiskFileSource(self.os_path, filename))
            if filename.startswith('archive-') and include_archive_files:
                rv.add_file_source(DiskFileSource(self.os_path, filename))
        return rv

    @classmethod
    def files_from_bundle(
            cls, budle_file_source: BrowsableFileSource,
            include_raw_files: bool,
            include_archive_files: bool) -> FileSource:
        rv = CombinedFileSource()
        for filename in budle_file_source.directory_list(''):
            if filename.startswith('raw-') and include_raw_files:
                rv.add_file_source(budle_file_source.sub_source(filename))
            if filename.startswith('archive-') and include_archive_files:
                rv.add_file_source(budle_file_source.sub_source(filename))
        return rv


class UploadBundle:
    '''
    Class for handling file-related logic for an *upload bundle*. Upload bundles are used
    to import and export uploads between different NOMAD installations.
    '''
    def __init__(self, path: str):
        ''' Creates an UploadBundle instance. The `path` should denote a zipfile or a folder. '''
        self.path = path
        self.file_source: BrowsableFileSource = None
        self._bundle_info: Dict[str, Any] = None
        if os.path.isdir(path):
            self.file_source = DiskFileSource(path)
        else:
            assert zipfile.is_zipfile(path), '`path` must define a folder or a zipfile.'
            zip_file = zipfile.ZipFile(path, 'r')
            self.file_source = ZipFileSource(zip_file)

    @property
    def bundle_info(self) -> Dict[str, Any]:
        if self._bundle_info is None:
            with self.file_source.open('bundle_info.json', 'rt') as f:
                self._bundle_info = json.load(f, cls=StandardJSONDecoder)
        return self._bundle_info

    def import_upload_files(
            self, include_raw_files: bool, include_archive_files: bool,
            move_files: bool) -> UploadFiles:
        '''
        Creates an :class:`UploadFiles` object of the right type and imports the selected
        files to it. The target folder must not already exist.
        '''
        try:
            upload_files: UploadFiles = None
            upload_id: str = self.bundle_info['upload_id']
            published: bool = self.bundle_info['upload']['published']
            cls = PublicUploadFiles if published else StagingUploadFiles
            assert not os.path.exists(cls.base_folder_for(upload_id)), 'Upload folder already exists'
            upload_files = cls(upload_id, is_authorized=lambda: True, create=True)
            import_file_source = upload_files.files_from_bundle(
                self.file_source, include_raw_files, include_archive_files)
            import_file_source.to_disk(upload_files.os_path, move_files=move_files, overwrite=True)
            return upload_files
        except Exception:
            # Some thing went wrong. Delete the files and re-raise the original exception
            if upload_files:
                upload_files.delete()
            raise

    def close(self):
        self.file_source.close()

    def delete(self, include_parent_folder: bool = False):
        '''
        Deletes the bundle files. If `include_parent_folder` is set, and the parent folder
        is empty, it is also deleted.
        '''
        self.close()
        if os.path.exists(self.path):
            PathObject(self.path).delete()
        if include_parent_folder:
            parent_folder = os.path.dirname(self.path)
            if not os.listdir(parent_folder):
                PathObject(parent_folder).delete()
