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
import React, { useContext } from 'react'
import PropTypes from 'prop-types'
import { Grid } from '@material-ui/core'
import { FilterSubMenu, filterMenuContext } from './FilterMenu'
import InputText from '../input/InputText'
import InputCheckboxes from '../input/InputCheckboxes'
import InputSelect from '../input/InputSelect'

const FilterSubMenuSymmetry = React.memo(({
  value,
  ...rest
}) => {
  const {selected} = useContext(filterMenuContext)
  const visible = value === selected

  return <FilterSubMenu value={value} {...rest}>
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <InputCheckboxes
          quantity="results.material.symmetry.bravais_lattice"
          visible={visible}
          xs={6}
        />
      </Grid>
      <Grid item xs={12}>
        <InputCheckboxes
          quantity="results.material.symmetry.crystal_system"
          visible={visible}
          xs={6}
        />
      </Grid>
      <Grid item xs={12}>
        <InputSelect
          quantity="results.material.symmetry.structure_name"
          visible={visible}
        />
      </Grid>
      <Grid item xs={12}>
        <InputSelect
          quantity="results.material.symmetry.strukturbericht_designation"
          visible={visible}
        />
      </Grid>
      <Grid item xs={12}>
        <InputText
          quantity="results.material.symmetry.space_group_symbol"
        />
      </Grid>
      <Grid item xs={12}>
        <InputText
          quantity="results.material.symmetry.point_group"
        />
      </Grid>
      <Grid item xs={12}>
        <InputText
          quantity="results.material.symmetry.hall_symbol"
        />
      </Grid>
      <Grid item xs={12}>
        <InputText
          quantity="results.material.symmetry.prototype_aflow_id"
        />
      </Grid>
    </Grid>
  </FilterSubMenu>
})
FilterSubMenuSymmetry.propTypes = {
  value: PropTypes.string
}

export default FilterSubMenuSymmetry
