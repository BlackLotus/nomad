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
NOMAD's file storage implementation
===================================

This file storage abstraction currently uses the object storage API
http://minio.io to manage and organize files. Object storage
organizes files in *buckets/ids*, with small amounts of *buckets* and virtually
unlimited numbers of *ids*. *Ids* can contain delimiters like `/` to mimic
filesystem structure. There is a 1024 utf-8 character limit on *id* length.

The file storage is organized in multiple buckets:

* *uploads*: used for uploaded user code input/output archives. Currently only .zip files \
are suported

Presigned URLs
--------------
Users (or GUI clients) can upload files directly to the object storage system. To avoid
authentication hassly, presigned URLs can be created that can be used directly to safely
*PUT* files.

.. autofunction:: nomad.files.get_presigned_upload_url
.. autofunction:: nomad.files.create_curl_upload_cmd
"""
import sys
import os
from os.path import join
from zipfile import ZipFile, BadZipFile
import shutil
from minio import Minio
import minio.error
import logging
import itertools

import nomad.config as config

logger = logging.getLogger(__name__)

_client = None

if _client is None and 'sphinx' not in sys.modules:
    _client = Minio('%s:%s' % (config.minio.host, config.minio.port),
                    access_key=config.minio.accesskey,
                    secret_key=config.minio.secret,
                    secure=False)

    # ensure all neccessary buckets exist
    try:
        _client.make_bucket(bucket_name=config.s3.uploads_bucket)
        logger.info("Created uploads bucket with name %s." % config.s3.uploads_bucket)
    except minio.error.BucketAlreadyOwnedByYou:
        logger.debug(
            "Uploads bucket with name %s already existed." % config.s3.uploads_bucket)


def get_presigned_upload_url(upload_id: str) -> str:
    """Generates a presigned upload URL.

    Presigned URL allows users (and their client programs) to safely *PUT*
    a single file without further authorization or API to the *uploads* bucket
    using the given ``upload_id``. Example usages for presigned URLs include
    browser based uploads or simple *curl* commands (see also :func:`create_curl_upload_cmd`).

    Args:
        upload_id: The upload id for the uploaded file.

    Returns:
        The presigned URL string.
    """
    return _client.presigned_put_object(config.s3.uploads_bucket, upload_id)


def create_curl_upload_cmd(presigned_url, file_dummy='<ZIPFILE>'):
    """Creates a readymade curl command for uploading.

    Args:
        presigned_url: The presigned URL to base the command on.

    Kwargs:
        file_dummy: A placeholder for the file that the user/client has to replace.

    Returns:
        The curl shell command with correct method, url, headers, etc.
    """
    headers = 'Content-Type: application/octet-steam'
    return 'curl -X PUT "%s" -H "%s" -F file=@%s' % (presigned_url, headers, file_dummy)


def upload(upload_id):
    return Upload(upload_id)


def upload_put_handler(func):
    def upload_notifications(events):
        # The given events is a generator that will block and yield indefinetely.
        # Therefore, we have to use generator expressions and must not use list
        # comprehension. Same for chain vs chain.from_iterable.
        nested_event_records = (event['Records'] for event in events)
        event_records = itertools.chain.from_iterable(nested_event_records)

        for event_record in event_records:
            try:
                event_name = event_record['eventName']
                if event_name == 's3:ObjectCreated:Put':
                    logger.debug('Received bucket upload event of type %s.' % event_name)
                    upload_id = event_record['s3']['object']['key']
                    yield upload_id
                else:
                    logger.debug('Unhandled bucket event of type %s.' % event_name)
            except KeyError:
                logger.warning(
                    'Unhandled bucket event due to unexprected event format: %s' %
                    event_record)

    def wrapper(*args, **kwargs):
        logger.info('Start listening to uploads notifications.')

        events = _client.listen_bucket_notification(config.s3.uploads_bucket)

        upload_ids = upload_notifications(events)
        for upload_id in upload_ids:
            try:
                func(upload_id)
            except StopIteration:
                # Using StopIteration to allow clients to stop handling of events.
                logging.debug(
                    'Handling of upload notifications was stopped via StopIteration.')
                return
            except Exception as e:
                logger.error(
                    'Unexpected exception in upload handler for upload:id:' %
                    upload_id, exc_info=e)

    return wrapper


class UploadError(Exception):
    IMPLEMENTATION_ERROR = 'implementation error'
    NOT_ZIP = 'upload is not a zip file'

    def __init__(self, msg, cause, code=IMPLEMENTATION_ERROR):
        super().__init__(msg, cause)
        self.code = code


class Upload():
    def __init__(self, upload_id):
        self.upload_id = upload_id
        self.upload_file = '%s/uploads/%s.zip' % (config.fs.tmp, upload_id)
        self.upload_extract_dir = '%s/uploads_extracted/%s' % (config.fs.tmp, upload_id)
        self.filelist = None

        try:
            _client.stat_object(config.s3.uploads_bucket, upload_id)
        except minio.error.NoSuchKey:
            raise KeyError(self.upload_id)

    # There is not good way to capsule decorators in a class:
    # https://medium.com/@vadimpushtaev/decorator-inside-python-class-1e74d23107f6
    class Decorators:
        @classmethod
        def log_upload_error(cls, decorated):
            def wrapper(self, *args, **kwargs):
                try:
                    return decorated(self, *args, **kwargs)
                except Exception as e:
                    msg = 'Could not %s upload %s.' % (decorated.__name__, self.upload_id)
                    logger.error(msg, exc_info=e)
                    raise UploadError(msg, e)
            return wrapper

    @Decorators.log_upload_error
    def open(self):
        try:
            _client.fget_object(config.s3.uploads_bucket, self.upload_id, self.upload_file)
        except minio.error.NoSuchKey:
            raise KeyError(self.upload_id)

        zipFile = None
        try:
            zipFile = ZipFile(self.upload_file)
            zipFile.extractall(self.upload_extract_dir)
            self.filelist = [zipInfo.filename for zipInfo in zipFile.filelist]
        except BadZipFile as e:
            raise UploadError('Upload is not a zip file', e, UploadError.NOT_ZIP)
        finally:
            if zipFile is not None:
                zipFile.close()

    @Decorators.log_upload_error
    def close(self):
        try:
            os.remove(self.upload_file)
            shutil.rmtree(self.upload_extract_dir)
        except FileNotFoundError:
            raise KeyError(self.upload_id)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        self.close()

    @Decorators.log_upload_error
    def open_file(self, filename, *args, **kwargs):
        return open(self.get_path(filename), *args, **kwargs)

    def get_path(self, filename):
        return join(self.upload_extract_dir, filename)
