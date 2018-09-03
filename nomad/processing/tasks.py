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

from typing import List
from celery import Task, chord, group
from celery.canvas import Signature
from datetime import datetime

from nomad import files, utils
from nomad.parsing import parsers, parser_dict
from nomad.normalizing import normalizers
import nomad.patch  # pylint: disable=unused-import

from nomad.processing.app import app
from nomad.processing.state import UploadProc, CalcProc


def _report_progress(task, dct):
    if not task.request.called_directly:
        task.update_state(state='PROGRESS', meta=dct)


@app.task(bind=True, name='extracting')
def extracting_task(task: Task, proc: UploadProc) -> UploadProc:
    """
    The task that extracts an already uploaded file. It goes through all files in
    the upload and identifies parser/mainfile matches. The matched parser, mainfile
    pairs are stored in the upload state.

    Arguments:
        proc: The :class:`UploadProc` instance that represents the upload processing.

    Returns: an updated version of the upload processing state.
    """
    logger = utils.get_logger(__name__, task=task.name, upload_id=proc.upload_id)
    if not proc.continue_with(task.name):
        return proc

    _report_progress(task, proc)

    try:
        upload = files.Upload(proc.upload_id)
        upload.open()
        logger.debug('Opened upload')
    except KeyError as e:
        logger.info('Process request for non existing upload')
        proc.fail(e)
        return proc
    except files.UploadError as e:
        logger.info('Could not open upload', error=str(e))
        proc.fail(e)
        return proc
    except Exception as e:
        logger.error('Unknown exception', exc_info=e)
        proc.fail(e)
        return proc

    logger.debug('Upload opened')

    try:
        proc.upload_hash = upload.hash()
    except files.UploadError as e:
        logger.error('Could not create upload hash', error=str(e))
        proc.fail(e)
        return proc

    from nomad.data import Calc
    if Calc.upload_exists(proc.upload_hash):
        logger.info('Upload hash doublet')
        proc.fail('The same file was already uploaded and processed.')
        return proc

    try:
        # TODO: deal with multiple possible parser specs
        for filename in upload.filelist:
            for parser in parsers:
                try:
                    if parser.is_mainfile(filename, lambda fn: upload.open_file(fn)):
                        tmp_mainfile = upload.get_path(filename)
                        calc_proc = CalcProc(filename, parser.name, tmp_mainfile)
                        proc.calc_procs.append(calc_proc)
                except Exception as e:
                    logger.warn('Exception while matching pot. mainfile.', mainfile=filename)
                    proc.warnings.append('Exception while matching pot. mainfile %s.' % filename)

    except files.UploadError as e:
        logger.warn('Could find parse specs in open upload', error=str(e))
        proc.fail(e)
        return proc

    return proc


@app.task(bind=True, name='cleanup')
def cleanup_task(task, calc_procs: List[CalcProc], upload_proc: UploadProc) -> UploadProc:
    """
    This task is used to removed any extracted files after the upload completed processing.

    Arguments:
        calc_procs: a list of cacl processing states
        upload_proc: the upload processing state

    Returns: an updated upload processing state
    """
    logger = utils.get_logger(__name__, task=task.name, upload_id=upload_proc.upload_id)
    if upload_proc.continue_with(task.name):

        _report_progress(task, upload_proc)

        try:
            upload = files.Upload(upload_proc.upload_id)
        except KeyError as e:
            logger.warn('Upload does not exist')
            upload_proc.fail(e)
            return upload_proc

        try:
            upload.close()
        except Exception as e:
            logger.error('Could not close upload', exc_info=e)
            upload_proc.fail(e)
            return upload_proc

        logger.debug('Closed upload')
        upload_proc.success()

    return upload_proc


@app.task(bind=True, name='parse_all')
def parse_all_task(task: Task, upload_proc: UploadProc, cleanup: Signature) -> UploadProc:
    """
    Initiates the processing for all mainfail, parser pairs stored in the uploading
    processing state. Parsing is called async and in parallel via celery *chord*.

    Arguments:
        upload_proc: the upload processing state
        cleanup: a signature for the cleanup task that is used to call the clean up task
            when all parse tasks (i.e. the chord) finished

    Returns: an updated upload processing state
    """
    cleanup = cleanup.clone(args=(upload_proc,))
    if not upload_proc.continue_with(task.name):
        chord(group())(cleanup)
        return upload_proc

    # prepare the group of parallel calc processings
    parses = group(parse_task.s(calc_proc, upload_proc) for calc_proc in upload_proc.calc_procs)

    # save the calc processing task ids to the overall processing
    for idx, child in enumerate(parses.freeze().children):
        upload_proc.calc_procs[idx].celery_task_id = child.task_id

    # initiate the chord that runs calc processings first, and close_upload afterwards
    chord(parses)(cleanup)

    return upload_proc


@app.task(bind=True, name='parse')
def parse_task(self, proc: CalcProc, upload_proc: UploadProc) -> CalcProc:
    """
    This task processes a calculation based on a parser, mainfile pair. It reports
    intermediate progress via the logical *'tasks'* defined in the
    calculation processing state.

    Arguments:
        proc: the calculation processing state
        upload_proc: the upload processing state

    Returns: an updated calcualtion processing state.
    """
    assert upload_proc.upload_hash is not None

    upload_hash, parser, mainfile = upload_proc.upload_hash, proc.parser_name, proc.mainfile
    logger = utils.get_logger(
        __name__, task=self.name,
        upload_id=upload_proc.upload_id, upload_hash=upload_hash, mainfile=mainfile)

    # parsing
    proc.continue_with(parser)
    try:
        parser_backend = parser_dict[parser].run(proc.tmp_mainfile)
        if parser_backend.status[0] != 'ParseSuccess':
            error = parser_backend.status[1]
            logger.debug('Failed parsing', parser=parser, error=error)
            proc.fail(error)
            return proc
        logger.debug('Completed successfully', parser=parser)
    except Exception as e:
        logger.warn('Exception wile parsing', parser=parser, exc_info=e)
        proc.fail(e)
        return proc
    _report_progress(self, proc)

    # normalization
    for normalizer in normalizers:
        normalizer_name = normalizer.__name__
        proc.continue_with(normalizer_name)
        try:
            normalizer(parser_backend).normalize()
            if parser_backend.status[0] != 'ParseSuccess':
                error = parser_backend.status[1]
                logger.info('Failed run of %s: %s' % (normalizer, error))
                proc.fail(error)
                return proc
            logger.debug('Completed %s successfully' % normalizer)
        except Exception as e:
            logger.warn('Exception wile normalizing with %s' % normalizer, exc_info=e)
            proc.fail(e)
            return proc
    _report_progress(self, proc)

    # update search
    proc.continue_with('archiving')
    try:
        from nomad.data import Calc
        Calc.create_from_backend(
            parser_backend,
            upload_hash=upload_hash,
            calc_hash=proc.calc_hash,
            upload_id=upload_proc.upload_id,
            mainfile=mainfile,
            upload_time=datetime.now())
        logger.debug('Archived successfully')
    except Exception as e:
        logger.error('Failed to archive', exc_info=e)
        proc.fail(e)
        return proc
    _report_progress(self, proc)

    logger.debug('Completed processing')

    proc.success()
    return proc
