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
import React, { useCallback, useContext, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { Paper, IconButton, Tooltip } from '@material-ui/core'
import { useApi, withLoginRequired } from '../api'
import Page from '../Page'
import { useErrors } from '../errors'
import DetailsIcon from '@material-ui/icons/MoreHoriz'
import DeleteIcon from '@material-ui/icons/Delete'
import DOIIcon from '@material-ui/icons/Bookmark'
import { DatasetButton } from '../nav/Routes'
import {
  addColumnDefaults, combinePagination, Datatable, DatatableLoadMorePagination,
  DatatableTable, DatatableToolbar } from '../datatable/Datatable'
import Quantity from '../Quantity'

export const help = `
NOMAD allows you to create *datasets* from your data. A dataset is like a tag that you
cann attach to one or many entries. An entry can have abitrary many datasets assign.
This way you can create datasets that overlap or contain each other. Datasets work
very similar to labels, albums, or tags on other platforms.
`

const columns = [
  {
    key: 'dataset_id',
    render: dataset => <Quantity quantity={'dataset_id'} noTitle noWrap withClipboard data={dataset}/>
  },
  {key: 'dataset_name'},
  {key: 'doi', label: 'Digital object identifier (DOI)'},
  {
    key: 'dataset_create_time',
    label: 'Create time',
    render: dataset => new Date(dataset.dataset_create_time).toLocaleString()
  },
  {
    key: 'dataset_modified_time',
    label: 'Modify time',
    render: dataset => (dataset.dataset_modified_time ? new Date(dataset.dataset_modified_time).toLocaleString() : '')
  }
]

addColumnDefaults(columns, {align: 'left'})

const PageContext = React.createContext({})

const DatasetActions = React.memo(function VisitDatasetAction({data}) {
  const {api} = useApi()
  const {raiseError} = useErrors()
  const {refresh} = useContext(PageContext)

  const handleDelete = useCallback(() => {
    api.delete(`/datasets/${data.dataset_id}`)
      .then(refresh).catch(raiseError)
  }, [api, raiseError, data.dataset_id, refresh])

  const handleAssignDoi = useCallback(() => {
    api.post(`/datasets/${data.dataset_id}/action/doi`)
      .then(refresh).catch(raiseError)
  }, [api, raiseError, data.dataset_id, refresh])

  return <React.Fragment>
    <Tooltip title="Assign a DOI">
      <span>
        <IconButton onClick={handleAssignDoi} disabled={!!data.doi}>
          <DOIIcon />
        </IconButton>
      </span>
    </Tooltip>
    <Tooltip title="Delete the dataset">
      <span>
        <IconButton onClick={handleDelete} disabled={!!data.doi}>
          <DeleteIcon />
        </IconButton>
      </span>
    </Tooltip>
    <Tooltip title="Open the dataset">
      <DatasetButton component={IconButton} datasetId={data.dataset_id}>
        <DetailsIcon />
      </DatasetButton>
    </Tooltip>
  </React.Fragment>
})
DatasetActions.propTypes = {
  data: PropTypes.object.isRequired
}

function DatasetsPage() {
  const {api} = useApi()
  const errors = useErrors()
  const [data, setData] = useState(null)
  const [pagination, setPagination] = useState({
    page_size: 10,
    page: 1,
    order_by: 'created'
  })

  const load = useCallback(() => {
    const {page_size, page} = pagination
    api.get(`/datasets?page_size=${page_size}&page=${page}`)
      .then(setData)
      .catch(errors.raiseError)
  }, [pagination, setData, errors, api])

  useEffect(() => {
    load()
  }, [load])

  return <Page loading={!data}>
    <PageContext.Provider value={{refresh: load}}>
      {data &&
        <Paper>
          <Datatable
            columns={columns} selectedColumns={columns.map(column => column.key)}
            data={data.data || []}
            pagination={combinePagination(pagination, data.pagination)}
            onPaginationChanged={setPagination}
          >
            <DatatableToolbar title="Your datasets" />
            <DatatableTable actions={DatasetActions}>
              <DatatableLoadMorePagination />
            </DatatableTable>
          </Datatable>
        </Paper>
      }
    </PageContext.Provider>
  </Page>
}

export default withLoginRequired(DatasetsPage)
