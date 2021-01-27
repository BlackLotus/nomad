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
import DefaultEntryOverview from '../entry/DefaultEntryOverview'
import EMSEntryDetails from './EMSEntryDetails'

/**
 * Shows an informative overview about the selected entry.
 */
export default function EMSEntryOverview({repo, uploadId, calcId}) {
  return (
    <DefaultEntryOverview repo={repo} uploadId={uploadId} calcId={calcId}>
      <EMSEntryDetails data={repo}></EMSEntryDetails>
    </DefaultEntryOverview>
  )
}

EMSEntryOverview.propTypes = {
  repo: PropTypes.object.isRequired,
  uploadId: PropTypes.string.isRequired,
  calcId: PropTypes.string.isRequired
}
