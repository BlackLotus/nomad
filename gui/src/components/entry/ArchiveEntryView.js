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
import React from 'react'
import PropTypes from 'prop-types'
import { withStyles, Fab, Card, CardContent, Typography } from '@material-ui/core'
import { compose } from 'recompose'
import { withApi } from '../api'
import DownloadIcon from '@material-ui/icons/CloudDownload'
import Download from './Download'
import ArchiveBrowser from '../archive/ArchiveBrowser'
import { EntryPageContent } from './EntryPage'

export const help = `
The NOMAD **archive** provides data and meta-data in a common hierarchical format based on
well-defined quantity definitions that we call *metainfo*. This representation
is independent from the raw data format and provides a homogenous data stock.

You can click the various quantity values to see the quantity definition. Similarly,
you can click section names to get more information. Browse the *metainfo* to
learn more about NOMAD's archive format [here](/metainfo).
`

class ArchiveEntryView extends React.Component {
  static propTypes = {
    classes: PropTypes.object.isRequired,
    api: PropTypes.object.isRequired,
    info: PropTypes.object,
    raiseError: PropTypes.func.isRequired,
    uploadId: PropTypes.string.isRequired,
    entryId: PropTypes.string.isRequired
  }

  static styles = theme => ({
    archiveBrowser: {
      marginTop: theme.spacing(2)
    },
    error: {
      marginTop: theme.spacing(2)
    },
    downloadFab: {
      zIndex: 1,
      right: 32,
      bottom: 32,
      position: 'fixed !important'
    }
  })

  static defaultState = {
    data: null,
    doesNotExist: false
  }

  state = {
    ...ArchiveEntryView.defaultState
  }

  constructor(props) {
    super(props)
    this.unmounted = false
  }

  componentWillUnmount() {
    this.unmounted = true
  }

  componentDidMount() {
    this.updateArchive()
  }

  componentDidUpdate(prevProps) {
    if (prevProps.api !== this.props.api ||
        prevProps.uploadId !== this.props.uploadId ||
        prevProps.entryId !== this.props.entryId) {
      this.setState({...ArchiveEntryView.defaultState})
      this.updateArchive()
    }
  }

  updateArchive() {
    const {uploadId, entryId, api} = this.props
    api.archive(uploadId, entryId).then(data => {
      if (!this.unmounted) {
        this.setState({data: data})
      }
    }).catch(error => {
      if (!this.unmounted) {
        this.setState({data: null})
      }
      if (error.name === 'DoesNotExist') {
        this.setState({doesNotExist: true})
      } else {
        this.props.raiseError(error)
      }
    })
  }

  render() {
    const { classes, uploadId, entryId } = this.props
    const { data, doesNotExist } = this.state

    if (doesNotExist) {
      return (
        <EntryPageContent>
          <Typography className={classes.error}>
            No archive exists for this entry. Either the archive was not generated due
            to parsing or other processing errors (check the log tab), or the entry it
            self does not exist.
          </Typography>
        </EntryPageContent>
      )
    }

    return (
      <EntryPageContent width={'100%'} maxWidth={'undefined'}>
        {
          data && typeof data !== 'string'
            ? <div className={classes.archiveBrowser}>
              <ArchiveBrowser data={data} />
            </div> : <div>{
              data
                ? <div>
                  <Typography>Archive data is not valid JSON. Displaying plain text instead.</Typography>
                  <Card>
                    <CardContent>
                      <pre>{data || ''}</pre>
                    </CardContent>
                  </Card>
                </div>
                : <Typography>loading ...</Typography>
            }</div>
        }

        <Download
          classes={{root: classes.downloadFab}} tooltip="download calculation archive"
          component={Fab} className={classes.downloadFab} color="primary" size="medium"
          url={`archive/${uploadId}/${entryId}`} fileName={`${entryId}.json`}
        >
          <DownloadIcon />
        </Download>
      </EntryPageContent>
    )
  }
}

export default compose(
  withApi(false, true),
  withStyles(ArchiveEntryView.styles)
)(ArchiveEntryView)
