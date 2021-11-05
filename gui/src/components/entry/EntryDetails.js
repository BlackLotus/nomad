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
import Quantity from '../Quantity'
import { Formula } from './properties/MaterialCard'
import { Typography, Link, Tooltip, IconButton } from '@material-ui/core'
import { Link as RouterLink } from 'react-router-dom'
import { authorList } from '../../utils'
import { useApi } from '../api'
import { EntryButton } from '../nav/Routes'
import DetailsIcon from '@material-ui/icons/MoreHoriz'
import PublicIcon from '@material-ui/icons/Public'
import UploaderIcon from '@material-ui/icons/AccountCircle'
import SharedIcon from '@material-ui/icons/SupervisedUserCircle'
import PrivateIcon from '@material-ui/icons/VisibilityOff'
import { makeStyles } from '@material-ui/core/styles'

export const MethodMetadata = React.memo(({data}) => {
  const methodQuantities = []
  const addMethodQuantities = (obj, parentKey) => {
    const children = {}
    Object.keys(obj).forEach(key => {
      const value = obj[key]
      if (Array.isArray(value) || typeof value === 'string') {
        if (value.length > 0) {
          methodQuantities.push({
            quantity: `${parentKey}.${key}`,
            label: key.replace(/_/g, ' ')
          })
        }
      } else if (value instanceof Object) {
        children[key] = value
      }
    })
    Object.keys(children).forEach(key => addMethodQuantities(children[key], `${parentKey}.${key}`))
  }
  if (data?.results?.method) {
    addMethodQuantities(data.results.method, 'results.method')
  }

  return <Quantity flex>
    {methodQuantities.map(({...quantityProps}) => (
      <Quantity
        key={quantityProps.quantity}
        {...quantityProps}
        noWrap
        data={data}
        hideIfUnavailable
      />
    ))}
  </Quantity>
})
MethodMetadata.propTypes = {
  data: PropTypes.object
}

export const DomainMetadata = React.memo(({data}) => {
  return <>
    <Quantity flex>
      <Formula data={data} />
      <Quantity quantity="results.material.material_name" data={data} label="material name" />
    </Quantity>
    <MethodMetadata data={data} />
  </>
})
DomainMetadata.propTypes = {
  data: PropTypes.object
}

export const UserMetadata = React.memo(({data}) => {
  return (
    <div>
      <Quantity quantity='comment' placeholder='no comment' data={data} />
      <Quantity quantity='references' placeholder='no references' data={data}>
        {data.references && <div style={{display: 'inline-grid'}}>
          {(data.references || []).map(ref => <Typography key={ref} noWrap>
            <Link href={ref}>{ref}</Link>
          </Typography>)}
        </div>}
      </Quantity>
      <Quantity quantity='authors' data={data}>
        <Typography>
          {authorList(data)}
        </Typography>
      </Quantity>
      <Quantity quantity='datasets' placeholder='no datasets' data={data}>
        <div>
          {(data.datasets || []).map(ds => (
            <Typography key={ds.dataset_id}>
              <Link component={RouterLink} to={`/dataset/id/${ds.dataset_id}`}>{ds.name}</Link>
              {ds.doi ? <span>&nbsp; (<Link href={`https://dx.doi.org/${ds.doi}`}>{ds.doi}</Link>)</span> : <React.Fragment/>}
            </Typography>))}
        </div>
      </Quantity>
    </div>
  )
})
UserMetadata.propTypes = {
  data: PropTypes.object.isRequired
}

export const EntryIds = React.memo(({data}) => {
  return (
    <div>
      <Quantity column >
        {/* <Quantity quantity="pid" label='PID' placeholder="not yet assigned" noWrap data={data} withClipboard /> */}
        <Quantity quantity="calc_id" label="entry id" noWrap withClipboard data={data} />
        <Quantity quantity="raw_id" label="raw id" noWrap withClipboard data={data} />
        <Quantity quantity="external_id" label="external id" noWrap withClipboard data={data} />
        <Quantity quantity="mainfile" noWrap ellipsisFront data={data} withClipboard />
        <Quantity quantity="upload_id" label="upload id" data={data} noWrap withClipboard>
          <Typography style={{flexGrow: 1}}>
            <Link component={RouterLink} to={`/uploads/${data.upload_id}`}>{data.upload_id}</Link>
          </Typography>
        </Quantity>
      </Quantity>
    </div>
  )
})
EntryIds.propTypes = {
  data: PropTypes.object.isRequired
}

export function Published(props) {
  const {user} = useApi()
  const {entry} = props
  if (entry.published) {
    if (entry.with_embargo) {
      if (user && entry.main_author.user_id === user.sub) {
        if (entry.viewers.length === 1) {
          return <Tooltip title="published with embargo by you and only accessible by you">
            <UploaderIcon color="error" />
          </Tooltip>
        } else {
          return <Tooltip title="published with embargo by you and only accessible to you and the specified coauthors and reviewers">
            <SharedIcon color="error" />
          </Tooltip>
        }
      } else if (user && entry.coauthors.find(user => user.user_id === user.sub)) {
        return <Tooltip title="published with embargo and visible to you as a coauthor">
          <SharedIcon color="error" />
        </Tooltip>
      } else if (user && entry.reviewers.find(user => user.user_id === user.sub)) {
        return <Tooltip title="published with embargo and visible to you as a reviewer">
          <SharedIcon color="error" />
        </Tooltip>
      } else {
        if (user) {
          return <Tooltip title="published with embargo and not accessible by you">
            <PrivateIcon color="error" />
          </Tooltip>
        } else {
          return <Tooltip title="published with embargo and might become accessible after login">
            <PrivateIcon color="error" />
          </Tooltip>
        }
      }
    } else {
      return <Tooltip title="published and accessible by everyone">
        <PublicIcon color="primary" />
      </Tooltip>
    }
  } else {
    return <Tooltip title="you have not published this entry yet">
      <UploaderIcon color="error"/>
    </Tooltip>
  }
}
Published.propTypes = {
  entry: PropTypes.object.isRequired
}

export const VisitEntryAction = React.memo(function VisitEntryAction({data, ...props}) {
  const {user} = useApi()
  const hide = data.with_embargo && !user && !data.viewers.find(viewer => viewer.user_id === user.sub)
  if (hide) {
    return ''
  }

  return <Tooltip title="Show raw files and archive">
    <EntryButton {...props} entryId={data.entry_id} uploadId={data.upload_id} />
  </Tooltip>
})
VisitEntryAction.propTypes = {
  data: PropTypes.object.isRequired
}

export const EntryRowActions = React.memo((props) => {
  return <VisitEntryAction {...props} component={IconButton}><DetailsIcon/></VisitEntryAction>
})

const useEntryDetailsStyles = makeStyles(theme => ({
  entryDetails: {
    paddingTop: theme.spacing(2),
    paddingLeft: theme.spacing(2),
    paddingRight: theme.spacing(2)
  },
  entryDetailsContents: {
    display: 'flex',
    width: '100%',
    margin: '0'
  },
  entryDetailsRow: {
    paddingRight: theme.spacing(3)
  },
  entryDetailsActions: {
    display: 'flex',
    flexBasis: 'auto',
    flexGrow: 0,
    flexShrink: 0,
    justifyContent: 'flex-end',
    marginBottom: theme.spacing(1),
    marginTop: theme.spacing(2)
  }
}))

export const EntryDetails = React.memo(({data}) => {
  const classes = useEntryDetailsStyles()

  return (
    <div className={classes.entryDetails}>
      <div className={classes.entryDetailsContents}>
        <div className={classes.entryDetailsRow}>
          <DomainMetadata data={data} />
        </div>

        <div className={classes.entryDetailsRow} style={{flexGrow: 1, minWidth: 'fit-content'}}>
          <Quantity className={classes.entryDetailsRow} column>
            <Quantity quantity='comment' placeholder='no comment' data={data} />
            <Quantity quantity='references' placeholder='no references' data={data}>
              {data.references && <div style={{display: 'inline-grid'}}>
                {(data.references || []).map(ref => <Typography key={ref} noWrap>
                  <Link href={ref}>{ref}</Link>
                </Typography>)}
              </div>}
            </Quantity>
            <Quantity quantity='authors' data={data}>
              <Typography>
                {authorList(data)}
              </Typography>
            </Quantity>
            <Quantity quantity='datasets' placeholder='no datasets' data={data}>
              <div>
                {(data.datasets || []).map(ds => (
                  <Typography key={ds.dataset_id}>
                    <Link component={RouterLink} to={`/dataset/id/${ds.dataset_id}`}>{ds.dataset_name}</Link>
                    {ds.doi ? <span>&nbsp; (<Link href={`https://dx.doi.org/${ds.doi}`}>{ds.doi}</Link>)</span> : <React.Fragment/>}
                  </Typography>))}
              </div>
            </Quantity>
          </Quantity>
        </div>

        <div className={classes.entryDetailsRow} style={{maxWidth: '33%', paddingRight: 0}}>
          <Quantity column >
            {/* <Quantity quantity="pid" label='PID' placeholder="not yet assigned" noWrap data={data} withClipboard /> */}
            <Quantity quantity="calc_id" label="entry id" noWrap withClipboard data={data} />
            <Quantity quantity="raw_id" label="raw id" noWrap withClipboard data={data} />
            <Quantity quantity="external_id" label="external id" noWrap withClipboard data={data} />
            <Quantity quantity="mainfile" noWrap ellipsisFront data={data} withClipboard />
            <Quantity quantity="upload_id" label="upload id" data={data} noWrap withClipboard>
              <Typography style={{flexGrow: 1}}>
                <Link component={RouterLink} to={`/uploads/${data.upload_id}`}>{data.upload_id}</Link>
              </Typography>
            </Quantity>
          </Quantity>
        </div>
      </div>

      <div className={classes.entryDetailsActions}>
        <VisitEntryAction color="primary" data={data}>
          Show raw files and archive
        </VisitEntryAction>
      </div>
    </div>
  )
})
EntryDetails.propTypes = {
  data: PropTypes.object.isRequired
}

export default EntryDetails
