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

import React, { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { Paper, Link } from '@material-ui/core'
import EntryDetails, { EntryRowActions } from '../entry/EntryDetails'
import {
  addColumnDefaults,
  Datatable, DatatablePagePagination, DatatableTable,
  DatatableToolbar, DatatableToolbarActions } from '../datatable/Datatable'
import EntryDownloadButton from '../entry/EntryDownloadButton'
import EditUserMetadataDialog from '../entry/EditUserMetadataDialog'

const columns = [
  {key: 'entry_id', align: 'left'},
  {key: 'mainfile', align: 'left'},
  {key: 'parser_name', align: 'left'},
  {key: 'process_status', align: 'left'},
  {key: 'complete_time', align: 'left'},
  {key: 'comment', sortable: false, align: 'left'},
  {
    key: 'references',
    sortable: false,
    align: 'left',
    render: row => {
      const refs = row.references || []
      if (refs.length > 0) {
        return (
          <div style={{display: 'inline'}}>
            {refs.map((ref, i) => <span key={ref}>
              <Link href={ref}>{ref}</Link>{(i + 1) < refs.length ? ', ' : <React.Fragment/>}
            </span>)}
          </div>
        )
      } else {
        return <i>no references</i>
      }
    }
  },
  {
    key: 'datasets',
    align: 'left',
    render: entry => {
      const datasets = entry.datasets || []
      if (datasets.length > 0) {
        return datasets.map(dataset => dataset.name).join(', ')
      } else {
        return <i>no datasets</i>
      }
    }
  }
]

addColumnDefaults(columns)

const defaultSelectedColumns = [
  'entry_id',
  'mainfile',
  'parser_name',
  'complete_time']

export default function ProcessingTable(props) {
  const [selected, setSelected] = useState([])
  const {data, pagination, onPaginationChanged, upload} = props

  const selectedQuery = useMemo(() => {
    if (selected === 'all') {
      return {'upload_id': upload.upload_id}
    }

    return {entry_id: selected.map(data => data.entry_id)}
  }, [selected, upload])

  return <Paper>
    <Datatable
      columns={columns} shownColumns={defaultSelectedColumns} {...props}
      selected={selected} onSelectedChanged={setSelected}
    >
      <DatatableToolbar title={`${pagination.total} search results`}>
        <DatatableToolbarActions selection>
          <EntryDownloadButton tooltip="Download files" query={selectedQuery} />
          {!upload.published && <EditUserMetadataDialog
            example={selected === 'all' ? data[0] : selected[0]}
            query={selectedQuery}
            total={pagination.total}
            onEditComplete={() => onPaginationChanged({...pagination})} // simply trigger a refresh
            buttonProps={{variant: 'contained', color: 'primary', disabled: upload?.process_running}}
            withoutLiftEmbargo={!upload.published}
          />}
        </DatatableToolbarActions>
      </DatatableToolbar>
      <DatatableTable actions={EntryRowActions} details={EntryDetails}>
        <DatatablePagePagination pageSizeValues={[5, 10, 50, 100]} />
      </DatatableTable>
    </Datatable>
  </Paper>
}
ProcessingTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object).isRequired,
  upload: PropTypes.object.isRequired,
  pagination: PropTypes.object.isRequired,
  onPaginationChanged: PropTypes.func.isRequired
}
