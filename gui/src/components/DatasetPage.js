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
import React, { useContext, useState, useEffect, useMemo } from 'react'
import PropTypes from 'prop-types'
import { Typography, makeStyles } from '@material-ui/core'
import { errorContext } from './errors'
import { useApi } from './api'
import Search from './search/Search'
import { SearchContext } from './search/SearchContext'
import { DOI } from './search/results/DatasetList'

export const help = `
This page allows you to **inspect** and **download** NOMAD datasets. It also allows you
to explore a dataset with similar controls that the search page offers.
`

const useStyles = makeStyles(theme => ({
  header: {
    display: 'flex',
    flexDirection: 'column'
  }
}))
const UserdataPage = React.memo(({match}) => {
  const styles = useStyles()
  const [dataset, setDataset] = useState()
  const {raiseError} = useContext(errorContext)
  const {api} = useApi()

  // Router provides the URL parameters via props, here we read the dataset ID.
  const datasetId = match?.params?.datasetId
  const datasetFilter = useMemo(() => ({'datasets.dataset_id': datasetId}), [datasetId])

  // Fetch the dataset information from API.
  useEffect(() => {
    api.datasets(datasetId)
      .then(setDataset)
      .catch(error => {
        setDataset(undefined)
        raiseError(error)
      })
  }, [datasetId, api, raiseError])

  // Shows basic dataset information above the searchbar
  return dataset && <SearchContext
    resource="entries"
    filtersLocked={datasetFilter}
  >
    <Search header={
      <div className={styles.header}>
        <Typography variant="h4">
          {dataset.name || (dataset.isEmpty && 'Empty or non existing dataset') || 'loading ...'}
        </Typography>
        <Typography>
          dataset{dataset.doi ? <span>, with DOI <DOI doi={dataset.doi} /></span> : ''}
        </Typography>
      </div>}
    />
  </SearchContext>
})
UserdataPage.propTypes = {
  match: PropTypes.object
}

export default UserdataPage
