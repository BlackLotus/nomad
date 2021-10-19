/*
 * Copyright The NOMAD Authors.
 *
 * This file is part of NOMAD. See https://nomad-lab.eu for further info.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import React, { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import Markdown from '../Markdown'
import {
  Paper, IconButton, Tooltip, Typography,
  Box, Divider, makeStyles } from '@material-ui/core'
import ClipboardIcon from '@material-ui/icons/Assignment'
import HelpDialog from '../Help'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import { guiBase, servicesUploadLimit } from '../../config'
import NewUploadButton from './NewUploadButton'
import { useApi, withLoginRequired } from '../api'
import Page from '../Page'
import { useErrors } from '../errors'
import PublicIcon from '@material-ui/icons/Public'
import UploaderIcon from '@material-ui/icons/AccountCircle'
import DetailsIcon from '@material-ui/icons/MoreHoriz'
import { UploadButton } from '../nav/Routes'
import {
  addColumnDefaults, combinePagination, Datatable, DatatableLoadMorePagination,
  DatatableTable, DatatableToolbar } from '../datatable/Datatable'
import TooltipButton from '../utils/TooltipButton'
import ReloadIcon from '@material-ui/icons/Autorenew'
import DeleteIcon from '@material-ui/icons/Delete'

export const help = `
NOMAD allows you to upload data. After upload, NOMAD will process your data: it will
identify the main output files of supported codes.
and then it will parse these files. The result will be a list of entries (one per each identified mainfile).
Each entry is associated with metadata. This is data that NOMAD acquired from your files and that
describe your calculations (e.g. chemical formula, used code, system type and symmetry, etc.).
Furthermore, you can provide your own metadata (comments, references, co-authors, etc.).
At first, uploaded data is only visible to you. Before others can actually see and download
your data, you need to publish your upload.

#### Prepare and upload files

Please put all the relevant files of all the calculations
you want to upload into a single \`*.zip\` or \`*.tar.gz\` archive.
We encourage you to add all code input and
output files, as well as any other auxiliary files that you might have created.
You can put data from multiple calculations into one file using as many directories as
you like. NOMAD will consider all files on a single directory to form a single entry.
Ideally, you put only files related to a single code run into each directory. If users
want to download an entry, they can download all files in the respective directory.
The directory structure can be nested.

Drop your archive file(s) on the dropbox. You can also click the dropbox to select the file from
your hard drive. Alternatively, you can upload files via the given shell command.
Replace \`<local_file>\` with your archive file. After executing the command,
return here and press the reload button below).

There is a limit of 10 unpublished uploads per user. Please accumulate all data into as
few uploads as possible. But, there is a also an upper limit of 32 GB per upload.
Please upload multiple archives, if you have more than 32 GB of data to upload.

#### The staging area

Uploaded data will not be public immediately. Below you will find all your unpublished and
published uploads. The unpublished uploads are only visible to you. You can see the
progress on the processing, you can review your uploads, and publish or delete them again.

Click on an upload to see more details about its contents. Click on processed calculations
to see their metadata, archive data, and a processing log. In the details view, you also
find buttons for editing user metadata, deleting uploads, and publishing uploads. Only
full uploads can be deleted or published.

#### Publishing and embargo

If you press publish, a dialog will appear that allows you to set an
*embargo* or publish your data as *Open Access* right away. The *embargo* allows you to share
data with selected users, create a DOI for your data, and later publish the data.
The *embargo* might last up to 36 month before data becomes public automatically.
During an *embargo* the data (and datasets created from this data) are already visible and
findable, but only you and users you share the data with (i.e. users you added under
*share with* when editing entries) can view and download the raw-data and archive.

#### Processing errors

We distinguish between uploads that fail processing completely and uploads that contain
entries that could not be processed. The former might be caused by issues during the
upload, bad file formats, etc. The latter (far more common) case means that not all of the provided
code output files could be parsed by our parsers. The processing logs of the failed entries might provide some insight.

You cannot publish uploads that failed processing completely. Frankly, in most
cases there won't be any data to publish anyways. In the case of failed processing of
some entries however, the data can still be published. You will be able to share it and create
DOIs for it, etc. The only shortcomings will be missing metadata (labeled *not processed*
or *unavailable*) and missing archive data. We continuously improve our parsers and
the now missing information might become available in the future automatically.

#### Co-Authors, References, Comments, Datasets, DOIs

You can edit additional *user metadata*. This data is assigned to individual entries, but
you can select and edit many entries at once. Edit buttons for user metadata are available
in many views on this web-page. For example, you can edit user metadata when you click on
an upload to open its details, and press the edit button there. User metadata can also
be changed after publishing data. The documentation on the [user data page](${guiBase}/userdata)
contains more information.
`

const columns = [
  {key: 'upload_id'},
  {key: 'upload_create_time'},
  {key: 'upload_name'},
  {key: 'last_status_message', label: 'Status'},
  {key: 'entries', render: upload => upload.entries, align: 'center'},
  {key: 'published', render: upload => <Published upload={upload} />, align: 'center'}
]

addColumnDefaults(columns, {align: 'left'})

const Published = React.memo(function Published({upload}) {
  if (upload.published) {
    return <Tooltip title="published upload">
      <PublicIcon color="primary" />
    </Tooltip>
  } else {
    return <Tooltip title="this upload is not yet published">
      <UploaderIcon color="error"/>
    </Tooltip>
  }
})
Published.propTypes = {
  upload: PropTypes.object.isRequired
}

const useUploadCommandStyles = makeStyles(theme => ({
  root: {
    width: '100%'
  },
  commandContainer: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center'
  },
  commandMarkup: {
    flexGrow: 1,
    marginRight: theme.spacing(1),
    overflow: 'hidden'
  }
}))

function UploadCommands({uploadCommands}) {
  const classes = useUploadCommandStyles()

  return <div className={classes.root}>
    <div className={classes.commandContainer}>
      <div className={classes.commandMarkup}>
        <Markdown>{`
          \`\`\`
            ${uploadCommands.upload_command}
          \`\`\`
        `}</Markdown>
      </div>
      <CopyToClipboard text={uploadCommands.upload_command} onCopy={() => null}>
        <Tooltip title="Copy command to clipboard">
          <IconButton>
            <ClipboardIcon />
          </IconButton>
        </Tooltip>
        {/* <button>Copy to clipboard with button</button> */}
      </CopyToClipboard>
      <HelpDialog icon={<DetailsIcon/>} maxWidth="md" title="Alternative shell commands" content={`
        As an experienced shell and *curl* user, you can modify the commands to
        your liking.

        The given command can be modified. To see progress on large files, use
        \`\`\`
          ${uploadCommands.upload_progress_command}
        \`\`\`
        To \`tar\` and upload multiple folders in one command, use
        \`\`\`
        ${uploadCommands.upload_tar_command}
        \`\`\`

        ### Form data vs. streaming
        NOMAD accepts stream data (\`-T <local_file>\`) (like in the
        examples above) or multi-part form data (\`-X PUT -f file=@<local_file>\`):
        \`\`\`
        ${uploadCommands.upload_command_form}
        \`\`\`
        We generally recommend to use streaming, because form data can produce very
        large HTTP request on large files. Form data has the advantage of carrying
        more information (e.g. the file name) to our servers (see below).

        #### Upload names
        With multi-part form data (\`-X PUT -f file=@<local_file>\`), your upload will
        be named after the file by default. With stream data (\`-T <local_file>\`)
        there will be no default name. To set a custom name, you can use the URL
        parameter \`name\`:
        \`\`\`
        ${uploadCommands.upload_command_with_name}
        \`\`\`
        Make sure to user proper [URL encoding](https://www.w3schools.com/tags/ref_urlencode.asp)
        and shell encoding, if your name contains spaces or other special characters.
      `}/>
    </div>
  </div>
}

const UploadActions = React.memo(function UploadActions({data}) {
  const {api} = useApi()
  const errors = useErrors()
  const [pagination] = useState({
    page_size: 10,
    page: 1,
    order_by: 'upload_create_time'
  })

  const handleReload = () => {
    const {page_size, page} = pagination
    api.get(`/uploads?page_size=${page_size}&page=${page}`)
      .then()
      .catch(errors.raiseError)
  }

  const handleDelete = () => {
    api.delete(`/uploads/${data.upload_id}`)
      .then(handleReload())
      .catch(errors.raiseError)
  }

  return <div>
    <IconButton disabled={data.published} onClick={handleDelete}>
      <Tooltip title="Delete this upload">
        <DeleteIcon />
      </Tooltip>
    </IconButton>
    <Tooltip title="Open this upload">
      <UploadButton component={IconButton} uploadId={data.upload_id}>
        <DetailsIcon />
      </UploadButton>
    </Tooltip>
  </div>
})
UploadActions.propTypes = {
  data: PropTypes.object.isRequired
}

UploadCommands.propTypes = {
  uploadCommands: PropTypes.object.isRequired
}

function UploadsPage() {
  const {api} = useApi()
  const errors = useErrors()
  const [data, setData] = useState(null)
  const [unpublished, setUnpublished] = useState(null)
  const [uploadCommands, setUploadCommands] = useState(null)
  const [pagination, setPagination] = useState({
    page_size: 10,
    page: 1,
    order_by: 'upload_create_time'
  })

  const handleReload = () => {
    const {page_size, page} = pagination
    api.get(`/uploads?page_size=${page_size}&page=${page}`)
      .then(setData)
      .catch(errors.raiseError)
  }

  useEffect(() => {
    api.get(`/uploads?is_published=false&page_size=0`)
      .then(setUnpublished)
      .catch(errors.raiseError)
  }, [setData, errors, api])

  const isDisable = unpublished ? (unpublished.pagination ? unpublished.pagination.total >= servicesUploadLimit : true) : true

  useEffect(() => {
    const {page_size, page} = pagination
    api.get(`/uploads?page_size=${page_size}&page=${page}`)
      .then(setData)
      .catch(errors.raiseError)
  }, [pagination, setData, errors, api])

  useEffect(() => {
    api.get('/uploads/command-examples')
      .then(setUploadCommands)
      .catch(errors.raiseError)
  }, [api, errors, setUploadCommands])

  return <Page loading={!(data && uploadCommands)}>
    <Box marginBottom={2}>
      <Typography>
        You can create an upload and upload files through this browser-based interface:
      </Typography>
    </Box>
    <NewUploadButton color="primary" isDisable={isDisable}/>
    <Box marginTop={4}>
      <Typography>
        Or, you can create an upload by sending a file-archive via shell command:
      </Typography>
    </Box>
    <Box marginBottom={-2}>
      {uploadCommands && <UploadCommands uploadCommands={uploadCommands}/>}
    </Box>
    {(data?.pagination?.total || 0) > 0 && <React.Fragment>
      <Box marginTop={2} marginBottom={2}>
        <Divider/>
      </Box>
      <Paper>
        <Datatable
          columns={columns} selectedColumns={columns.map(column => column.key)}
          data={data.data || []}
          pagination={combinePagination(pagination, data.pagination)}
          onPaginationChanged={setPagination}
        >
          <DatatableToolbar title="Your existing uploads">
            <TooltipButton
              title="Reload the uploads"
              component={IconButton}
              onClick={handleReload}
            >
              <ReloadIcon/>
            </TooltipButton>
          </DatatableToolbar>
          <DatatableTable actions={UploadActions}>
            <DatatableLoadMorePagination />
          </DatatableTable>
        </Datatable>
      </Paper>
    </React.Fragment>}
  </Page>
}

export default withLoginRequired(UploadsPage)
