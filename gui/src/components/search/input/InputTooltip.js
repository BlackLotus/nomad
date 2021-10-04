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
import { Tooltip } from '@material-ui/core'
import PropTypes from 'prop-types'

/**
 * The quantity label shown by all filter components.
 */
const InputTooltip = React.memo(({
  locked,
  disabled,
  children
}) => {
  return <Tooltip
    title={locked
      ? 'This filter is locked.'
      : disabled ? 'No values available with current query.' : ''
    }
    placement="bottom"
  >
    {children}
  </Tooltip>
})

InputTooltip.propTypes = {
  locked: PropTypes.bool,
  disabled: PropTypes.bool,
  children: PropTypes.node
}

InputTooltip.defaultProps = {
  underscores: false
}

export default InputTooltip
