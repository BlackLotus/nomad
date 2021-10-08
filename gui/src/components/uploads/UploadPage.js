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
import React, { useEffect, useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { makeStyles, Step, StepContent, StepLabel, Stepper, Typography, Link, Button,
  TextField, Tooltip, Box, Grid, FormControl, InputLabel, Select, MenuItem, FormHelperText,
  Input, DialogTitle, DialogContent, Dialog, LinearProgress, Paper, Slide, CircularProgress, IconButton} from '@material-ui/core'
import Dropzone from 'react-dropzone'
import UploadIcon from '@material-ui/icons/CloudUpload'
import { appBase } from '../../config'
import { CodeList } from '../About'
import { DoesNotExist, useApi, withLoginRequired } from '../api'
import { useParams } from 'react-router'
import { useHistory, useLocation } from 'react-router-dom'
import FilesBrower from './FilesBrowser'
import { useErrors } from '../errors'
import ProcessingTable from './ProcessingTable'
import EditIcon from '@material-ui/icons/Edit'
import DeleteIcon from '@material-ui/icons/Delete'
import MembersIcon from '@material-ui/icons/People'
import WithButton from '../utils/WithButton'
import PublishedIcon from '@material-ui/icons/Public'
import UnPublishedIcon from '@material-ui/icons/AccountCircle'
import Markdown from '../Markdown'
import EditUserMetadataDialog from '../entry/EditUserMetadataDialog'
import Page from '../Page'
import { getUrl } from '../nav/Routes'
import { combinePagination } from '../datatable/Datatable'

const useDropButtonStyles = makeStyles(theme => ({
  dropzone: {
    width: '100%'
  },
  dropzoneAccept: {
    '& button': {
      background: theme.palette.primary.main,
      color: theme.palette.common.white
    }
  },
  dropzoneReject: {
    '& button': {
      background: theme.palette.error.main,
      color: theme.palette.common.white
    }
  }
}))

function DropButton({onDrop, ...buttonProps}) {
  const classes = useDropButtonStyles()
  return <Dropzone
    accept={[
      'application/zip',
      'application/gzip',
      'application/bz2',
      'application/x-gzip',
      'application/x-bz2',
      'application/x-gtar',
      'application/x-tgz',
      'application/tar+gzip',
      'application/x-tar',
      'application/tar+bz2',
      'application/x-zip-compressed',
      'application/x-compressed',
      'application/x-zip']}
    className={classes.dropzone}
    activeClassName={classes.dropzoneAccept}
    rejectClassName={classes.dropzoneReject}
    onDrop={onDrop}
  >
    <Button
      variant="contained"
      color="default"
      startIcon={<UploadIcon/>}
      {...buttonProps}
    >
      click or drop files
    </Button>
  </Dropzone>
}
DropButton.propTypes = {
  onDrop: PropTypes.func
}

function UploadStatus({upload, ...props}) {
  if (!upload) {
    return <UnPublishedIcon color="default" {...props} />
  }
  if (upload.published) {
    return <Tooltip title="This upload is published and visible to everybody.">
      <PublishedIcon color="primary" {...props} />
    </Tooltip>
  }
  // TODO published with embargo
  if (!upload.published) {
    return <Tooltip title="This upload is not yet published and only visible to you.">
      <UnPublishedIcon color="error" {...props} />
    </Tooltip>
  }
}

const useUploadNameStyles = makeStyles(theme => ({
  edit: {
    display: 'flex',
    alignItems: 'center',
    '& button': {
      marginLeft: theme.spacing(2)
    }
  }
}))

function UploadName({name, onChange}) {
  const [edit, setEdit] = useState(false)
  const [value, setValue] = useState(null)
  const classes = useUploadNameStyles()

  const handleSave = () => {
    setEdit(false)
    if (onChange) {
      onChange(value)
    }
  }

  if (edit) {
    return <div className={classes.edit}>
      <TextField value={value} onChange={event => setValue(event.target.value)} fullWidth />
      <Button size="small" variant="contained" onClick={handleSave}>save</Button>
    </div>
  }

  return <WithButton size="small"
    icon={<EditIcon style={{fontSize: 24}} />} onClick={() => { setEdit(true); setValue(name) }}
  >
    <Typography variant="h6">
      {name || <i>unnamed upload</i>}
    </Typography>
  </WithButton>
}
UploadName.propTypes = {
  name: PropTypes.string,
  onChange: PropTypes.func
}

function PublishUpload({upload, onPublish}) {
  const [embargo, setEmbargo] = useState(upload.embargo_length === undefined ? 0 : upload.embargo_length)
  const handlePublish = () => {
    onPublish({embargo_length: embargo})
  }

  if (upload.published) {
    return <Markdown>{`
      This upload has already been published.
    `}</Markdown>
  }

  return <React.Fragment>
    <Markdown>{`
      If you agree this upload will be published and move out of your private staging
      area into the public NOMAD. This step is final. All public data will be made available under the Creative
      Commons Attribution license ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).

      If you wish, you can put an embargo on your data. Embargoed data is
      visible to and findable by others. This makes some metadata (e.g.
      chemical formula, system type, spacegroup, etc.) public, but the raw-file
      and archive contents remain hidden (except to you, and users you explicitly
      share the data with).
      You can already create datasets and assign DOIs for data with embargo, e.g.
      to put it into your unpublished paper.
      The embargo will last up to 36 month. Afterwards, your data will be made publicly
      available. You can also lift the embargo on entries at any time.
      This functionality is part of editing entries.
    `}</Markdown>
    <Box marginTop={2}>
      <Grid container direction="row" spacing={2}>
        <Grid item style={{width: 300}}>
          <FormControl style={{width: '100%'}}>
            <InputLabel shrink htmlFor="embargo-label-placeholder">
              Embargo period
            </InputLabel>
            <Select
              value={embargo}
              onChange={event => setEmbargo(event.target.value)}
              input={<Input name="embargo" id="embargo-label-placeholder" />}
              displayEmpty
              name="embargo"
              // className={classes.selectEmpty}
            >
              <MenuItem value={0}>
                <em>No embargo</em>
              </MenuItem>
              <MenuItem value={3}>3</MenuItem>
              <MenuItem value={6}>6</MenuItem>
              <MenuItem value={12}>12</MenuItem>
              <MenuItem value={24}>24</MenuItem>
              <MenuItem value={36}>36</MenuItem>
            </Select>
            <FormHelperText>{embargo > 0 ? 'months before the data becomes public' : 'publish without embargo'}</FormHelperText>
          </FormControl>
        </Grid>
        <Grid item>
          <Box marginTop={2} >
            <Button
              style={{height: 32, minWith: 100}}
              size="small" variant="contained"
              onClick={() => handlePublish()} color="primary" autoFocus
              disabled={upload.process_running}
            >
              {embargo > 0 ? 'Publish with embargo' : 'Publish'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  </React.Fragment>
}
PublishUpload.propTypes = {
  upload: PropTypes.object,
  onPublish: PropTypes.func
}

function LinearProgressWithLabel(props) {
  return (
    <Box display="flex" alignItems="center">
      <Box width="100%" mr={1}>
        <LinearProgress variant="determinate" {...props} />
      </Box>
      <Typography variant="body2" color="textSecondary">{`${Math.round(
        props.value
      )}%`}</Typography>
    </Box>
  )
}
LinearProgressWithLabel.propTypes = {
  value: PropTypes.number.isRequired
}

function ProcessingStatus({data}) {
  const {pagination, upload, processing_successful, processing_failed} = data
  let mainMessage = null
  if (upload.process_running) {
    mainMessage = 'Processing ...'
  } else {
    if (upload.process_status === 'SUCCESS') {
      mainMessage = 'Processing completed'
    } else if (upload.process_status === 'FAILURE') {
      mainMessage = 'Processing failed ' + upload.errors.join(', ')
    } else {
      mainMessage = 'Waiting for processing ...'
    }
  }
  return <Box marginTop={1} marginBottom={2}>
    <Typography>
      {mainMessage}, {processing_successful}/{pagination?.total} entries processed{(processing_failed > 0) && `, ${processing_failed} failed`}
    </Typography>
  </Box>
}
ProcessingStatus.propTypes = {
  data: PropTypes.object
}

const useStyles = makeStyles(theme => ({
  stepper: {
    backgroundColor: 'inherit'
  },
  stepContent: {
    marginBottom: theme.spacing(2)
  },
  status: {
    position: 'absolute',
    left: 0,
    right: 0,
    marginTop: -20,
    margin: -10,
    padding: 10,
    paddingTop: 20,
    zIndex: 1000
  }
}))

function UploadPage() {
  const classes = useStyles()
  const { uploadId } = useParams()
  const {api} = useApi()
  const errors = useErrors()
  const history = useHistory()
  const location = useLocation()

  const [pagination, setPagination] = useState({
    page_size: 5, page: 1, order: 'asc', order_by: 'process_status'
  })
  const [deleteClicked, setDeleteClicked] = useState(false)
  const [data, setData] = useState(null)
  const [uploading, setUploading] = useState(null)
  const upload = data?.upload
  const setUpload = useMemo(() => (upload) => {
    setData(data => ({...data, upload: upload}))
  }, [setData])

  const isProcessing = upload?.process_running

  const fetchData = useMemo(() => () => {
    api.get(`/uploads/${uploadId}/entries`, pagination)
      .then(results => setData(results))
      .catch((error) => {
        if (error instanceof DoesNotExist && deleteClicked) {
          history.push(getUrl('uploads', location))
        } else {
          errors.raiseError(error)
        }
      })
  }, [api, uploadId, pagination, deleteClicked, history, errors, location])

  // constant fetching of upload data when necessary
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(fetchData, 1000)
      return () => clearInterval(interval)
    }
  }, [fetchData, isProcessing])

  // initial fetching of upload data
  useEffect(fetchData, [fetchData])

  const handleDrop = (files) => {
    const formData = new FormData() // eslint-disable-line no-undef
    formData.append('file', files[0])
    setUploading(0)
    api.put(`/uploads/${uploadId}/raw`, formData, {
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        setUploading(percentCompleted)
      }
    })
      .then(results => setUpload(results.data))
      .catch(errors.raiseError)
      .finally(() => {
        setUploading(null)
      })
  }

  const handleNameChange = (name) => {
    api.put(`/uploads/${uploadId}/metadata?upload_name=${name}`)
      .then(results => setUpload(results.data))
      .catch(errors.raiseError)
  }

  const handlePublish = ({embargo_length}) => {
    api.post(`/uploads/${uploadId}/action/publish`, {
      embargo_length: embargo_length
    })
      .then(results => setUpload(results.data))
      .catch(errors.raiseError)
  }

  const handleDelete = () => {
    setDeleteClicked(true)
    api.delete(`/uploads/${uploadId}`)
      .then(results => setUpload(results.data))
      .catch(errors.raiseError)
  }

  if (!upload) {
    return <Page limitedWidth>
      <Typography>loading ...</Typography>
    </Page>
  }

  const isPublished = upload.published
  const isEmpty = upload.entries === 0

  return <Page limitedWidth>
    {(uploading || uploading === 0) && <Dialog open>
      <DialogTitle>Uploading file ...</DialogTitle>
      <DialogContent>
        <Box width={300}>
          <LinearProgressWithLabel value={uploading} />
        </Box>
      </DialogContent>
    </Dialog>}
    <Slide direction="down" in={isProcessing} mountOnEnter unmountOnExit>
      <Paper className={classes.status}>
        <Page limitedWidth>
          <Grid container spacing={2} alignItems="center">
            <Grid item>
              <CircularProgress />
            </Grid>
            <Grid item style={{flexGrow: 1}}>
              <Typography>Upload is processing ...</Typography>
              <Typography>{data.upload.current_process}</Typography>
            </Grid>
          </Grid>
        </Page>
      </Paper>
    </Slide>
    <Grid container spacing={2} alignItems="center">
      <Grid item>
        <UploadStatus upload={upload} fontSize="large" />
      </Grid>
      <Grid item style={{flexGrow: 1}}>
        <UploadName name={upload?.upload_name} onChange={handleNameChange} />
        <WithButton clipboard={uploadId}>
          <Typography>upload id: {uploadId}</Typography>
        </WithButton>
      </Grid>
      <Grid>
        <IconButton>
          <Tooltip title="Manage upload members">
            <MembersIcon />
          </Tooltip>
        </IconButton>
        <IconButton disabled={isPublished} onClick={handleDelete}>
          <Tooltip title="Manage delete the upload">
            <DeleteIcon />
          </Tooltip>
        </IconButton>
      </Grid>
    </Grid>
    <Stepper classes={{root: classes.stepper}} orientation="vertical" nonLinear>
      <Step expanded active={false}>
        <StepLabel>Prepare and upload your files</StepLabel>
        <StepContent>
          {isPublished && <Typography className={classes.stepContent}>
            This upload is published and it&apos;s files can&apos;t be modified anymore.
          </Typography>}
          {!isPublished && (
            <React.Fragment>
              <Typography className={classes.stepContent}>
                To prepare your data, simply use <b>zip</b> or <b>tar</b> to create a single file that contains
                all your files as they are. These .zip/.tar files can contain subdirectories and additional files.
                NOMAD will search through all files and identify the relevant files automatically.
                Each uploaded file can be <b>up to 32GB</b> in size, you can have <b>up to 10 unpublished
                uploads</b> simultaneously. Your uploaded data is not published right away.
                Find more details about uploading data in our <Link href={`${appBase}/docs/upload.html`}>documentation</Link> or visit
                our <Link href="https://nomad-lab.eu/repository-archive-faqs">FAQs</Link>.
                The following codes are supported: <CodeList withUploadInstructions />. Click
                the code to get more specific information about how to prepare your files.
              </Typography>
              <DropButton
                className={classes.stepContent}
                size="large"
                fullWidth onDrop={handleDrop}
                disabled={isProcessing} />
            </React.Fragment>
          )}
          <FilesBrower className={classes.stepContent} uploadId={uploadId} disabled={isProcessing} />
        </StepContent>
      </Step>
      <Step expanded={!isEmpty}>
        <StepLabel>Process data</StepLabel>
        <StepContent>
          <ProcessingStatus data={data} />
          <ProcessingTable
            upload={upload}
            data={data.data.map(entry => ({...entry.entry_metadata, ...entry}))}
            pagination={combinePagination(pagination, data.pagination)}
            onPaginationChanged={setPagination} />
        </StepContent>
      </Step>
      <Step expanded={!isEmpty}>
        <StepLabel>Edit metadata</StepLabel>
        <StepContent>
          <Typography className={classes.stepContent}>
            You can add more information about your data, like <i>comments</i>, <i>references</i> (e.g. links
            to publications), you can create <i>datasets</i> from your entries, or <i>share</i> private data
            with outhers (e.g. before publishing or after publishing with an embargo.).
            Please note that <b>we require you to list the <i>co-authors</i></b> before publishing.
          </Typography>
          <Typography className={classes.stepContent}>
            You can either select and edit individual entries from the list above, or
            edit all entries at once.
          </Typography>
          {!isEmpty && <EditUserMetadataDialog
            example={data.data[0].entry_metadata || {}}
            query={{'upload_id': [uploadId]}}
            total={data.pagination.total}
            onEditComplete={() => setPagination({...pagination})}
            buttonProps={{variant: 'contained', color: 'primary', disabled: isProcessing}}
            text={`Edit metadata of all ${data.pagination.total} entries`}
            withoutLiftEmbargo={!isPublished}
          />}
        </StepContent>
      </Step>
      <Step expanded={!isEmpty}>
        <StepLabel>Publish</StepLabel>
        <StepContent>
          {isPublished && <Typography>This upload has already been published.</Typography>}
          {!isPublished && <PublishUpload upload={upload} onPublish={handlePublish} />}
        </StepContent>
      </Step>
    </Stepper>
  </Page>
}

export default withLoginRequired(UploadPage)
