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
import React, { useState, useMemo, useEffect } from 'react'
import PropTypes from 'prop-types'
import { scale } from 'chroma-js'
import { useTheme } from '@material-ui/core/styles'
import Plot from './Plot'
import { withErrorHandler } from '../ErrorHandler'
import { toUnitSystem, Unit } from '../../units'

/**
 * A thin wrapper for the Plot-component that is used for plotting energy-volume
 * curves.
 */
const energyUnit = new Unit('joule')
const volumeUnit = new Unit('meter**3')
const lineStyles = ['solid', 'dot', 'dashdot']

const EnergyVolumeCurve = React.memo(({
  data,
  className,
  units,
  'data-testid': testID
}) => {
  const [finalData, setFinalData] = useState(data)
  const theme = useTheme()

  // Calculate color values for traces
  const colors = useMemo(() => {
    if (!data) {
      return
    }
    const nTraces = data.data.length
    return scale([theme.palette.primary.dark, theme.palette.secondary.light])
      .mode('lch').colors(nTraces)
  }, [data, theme])

  // Calculate indices that sort the data
  const indices = useMemo(() => {
    if (!data) {
      return [undefined, undefined, undefined]
    }

    // Get indices that sort the data by volume
    const nTraces = data.data.length
    const indices = new Array(nTraces)
    const volumes = data.data[0].volumes
    for (let i = 0; i < nTraces; ++i) indices[i] = i
    indices.sort((a, b) => {
      return volumes[a] < volumes[b] ? -1 : volumes[a] > volumes[b] ? 1 : 0
    })
    return indices
  }, [data])

  // Side effect that runs when the data that is displayed should change. By
  // running all this heavy stuff within useEffect (instead of e.g. useMemo),
  // the first render containing the placeholders etc. can be done as fast as
  // possible.
  useEffect(() => {
    if (!data) {
      return
    }

    const traces = []
    let i = 0
    for (let curve of data.data) {
      const trace = {
        x: toUnitSystem(indices.map(i => curve.volumes[i]), volumeUnit, units),
        y: toUnitSystem(indices.map(i => curve.energies[i]), energyUnit, units),
        name: curve.name,
        visible: i === 0 || 'legendonly',
        type: 'scatter',
        line: {
          dash: lineStyles[i % lineStyles.length],
          color: colors[i],
          width: 2
        }
      }
      traces.push(trace)
      ++i
    }
    setFinalData(traces)
  }, [data, units, theme, indices, colors])

  const plotLayout = useMemo(() => {
    if (!data) {
      return null
    }

    return {
      showlegend: true,
      legend: {
        x: 0.5,
        y: 1,
        xanchor: 'center'
      },
      xaxis: {
        title: {
          text: `Volume (${volumeUnit.label(units)})`
        },
        zeroline: false
      },
      yaxis: {
        title: {
          text: `Energy (${energyUnit.label(units)})`
        },
        zeroline: false
      }
    }
  }, [data, units])

  return <Plot
    data={finalData}
    layout={plotLayout}
    floatTitle="Energy volume curve"
    metaInfoLink={data?.m_path}
    className={className}
    data-testid={testID}
  />
})

EnergyVolumeCurve.propTypes = {
  data: PropTypes.oneOfType([
    PropTypes.bool, // Set to False to show NoData component
    PropTypes.shape({
      data: PropTypes.arrayOf(PropTypes.shape({
        volumes: PropTypes.arrayOf(PropTypes.number).isRequired,
        energies: PropTypes.arrayOf(PropTypes.number).isRequired,
        name: PropTypes.string.isRequired
      })).isRequired,
      m_path: PropTypes.string // Path of the section containing the data in the Archive
    })
  ]),
  className: PropTypes.string,
  units: PropTypes.object, // Contains the unit configuration
  'data-testid': PropTypes.string
}

export default withErrorHandler(EnergyVolumeCurve, 'Could not load energy volume curve.')
