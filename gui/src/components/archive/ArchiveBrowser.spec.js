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
import { range } from 'lodash'
import userEvent from '@testing-library/user-event'
import { screen, renderNoAPI } from '../conftest.spec'
import { expectPagination } from '../visualization/conftest.spec'
import { PropertyValuesList } from './ArchiveBrowser'
import { laneContext } from './Browser'

test.each([
  [15, 10, 5],
  [12, 10, 5]
])('test subsection with no pagination, items: %s, top: %s, bottom:%s', async (nItems, nTop, nBottom) => {
  const indices = range(nItems)
  const label = "subsection"
  const values = indices.map(i => (null))

  renderNoAPI(
    <laneContext.Provider value={{next: {}}}>
      <PropertyValuesList label={label} values={values} nTop={nTop} nBottom={nBottom} />
    </laneContext.Provider>
  )
  // Open section by clicking
  const labelItem = screen.getByText(label)
  await userEvent.click(labelItem)

  // Expect to find all items
  for (const i of indices) {
    screen.getByText(`${i}`)
  }
  // Pagination component should not be visible
  await expectPagination(false, false, false)
})

test.each([
  [30, 10, 5],
  [16, 10, 5]
])('test subsection with pagination, items: %s, top: %s, bottom:%s', async (nItems, nTop, nBottom) => {
  const indices = range(nItems)
  const label = "subsection"
  const values = indices.map(i => (null))

  renderNoAPI(
    <laneContext.Provider value={{next: {}}}>
      <PropertyValuesList label={label} values={values} nTop={nTop} nBottom={nBottom} />
    </laneContext.Provider>
  )
  // Open section by clicking
  const labelItem = screen.getByText(label)
  await userEvent.click(labelItem)

  // Expect to find top and bottom items
  for (const i of range(nTop)) {
    screen.getByText(`${i}`)
  }
  for (const i of range(nBottom)) {
    screen.getByText(`${nItems - i - 1}`)
  }
  // Both pagination components should be visible
  const downPagination = screen.getByTestId('propertyvalueslist-pagination-down')
  await expectPagination(true, false, false, downPagination)
  const upPagination = screen.getByTestId('propertyvalueslist-pagination-up')
  await expectPagination(true, false, false, upPagination)
})
