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
import React, { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import {
  Box,
  Typography
} from '@material-ui/core'
import DOS from './DOS'
import BandStructure from './BandStructure'
import BrillouinZone from './BrillouinZone'
import Placeholder from '../visualization/Placeholder'
import { RecoilRoot } from 'recoil'
import { unitsState } from '../archive/ArchiveBrowser'
import { makeStyles } from '@material-ui/core/styles'

function ElectronicStructureOverview({data, range, className, classes, raiseError}) {
  const [dosResetLayout] = useState({
    yaxis: {range: range}
  })
  const [bsResetLayout] = useState({
    yaxis: {range: range}
  })
  const [dosLayout, setDosLayout] = useState(dosResetLayout)
  const [bsLayout, setBsLayout] = useState(bsResetLayout)

  // Styles
  const useStyles = makeStyles((theme) => {
    return {
      row: {
        display: 'flex',
        flexDirection: 'row',
        justifyContent: 'flex-start',
        alignItems: 'center',
        width: '100%',
        height: '100%'
      },
      bz: {
        flex: '0 0 25%'
      },
      bs: {
        flex: '0 0 50%'
      },
      dos: {
        flex: '0 0 25%'
      }
    }
  })
  const style = useStyles(classes)

  // Synchronize panning between BS/DOS plots
  const handleBSRelayouting = useCallback((event) => {
    let update = {
      yaxis: {
        range: [event['yaxis.range[0]'], event['yaxis.range[1]']]
      }
    }
    setDosLayout(update)
  }, [])
  const handleDOSRelayouting = useCallback((event) => {
    let update = {
      yaxis: {
        range: [event['yaxis.range[0]'], event['yaxis.range[1]']]
      }
    }
    setBsLayout(update)
  }, [])

  return (
    <RecoilRoot>
      <Box className={style.row}>
        {data.bs
          ? <Box className={style.bz}>
            <Typography variant="subtitle1" align='center'>Brillouin zone</Typography>
            {data?.bs?.section_k_band
              ? <BrillouinZone
                data={data.bs.section_k_band}
                aspectRatio={0.5}
              ></BrillouinZone>
              : <Placeholder className={null} aspectRatio={1.1} variant="rect"></Placeholder>
            }
          </Box>
          : null
        }
        {data.bs
          ? <Box className={style.bs}>
            <Typography variant="subtitle1" align='center'>Band structure</Typography>
            {data?.bs?.section_k_band
              ? <BandStructure
                data={data.bs.section_k_band}
                layout={bsLayout}
                resetLayout={bsResetLayout}
                aspectRatio={1.0}
                unitsState={unitsState}
                onRelayouting={handleBSRelayouting}
              ></BandStructure>
              : <Placeholder className={null} aspectRatio={1.1} variant="rect"></Placeholder>
            }
          </Box>
          : null
        }
        {data.dos
          ? <Box className={style.dos}>
            <Typography variant="subtitle1" align='center'>Density of states</Typography>
            {data?.dos?.section_dos
              ? <DOS
                data={data.dos.section_dos}
                layout={dosLayout}
                resetLayout={dosResetLayout}
                aspectRatio={0.5}
                onRelayouting={handleDOSRelayouting}
                unitsState={unitsState}
              ></DOS>
              : <Placeholder className={null} aspectRatio={1.1} variant="rect"></Placeholder>
            }
          </Box>
          : null
        }
      </Box>
    </RecoilRoot>
  )
}

ElectronicStructureOverview.propTypes = {
  data: PropTypes.object,
  range: PropTypes.array,
  className: PropTypes.string,
  classes: PropTypes.object,
  raiseError: PropTypes.func
}
ElectronicStructureOverview.defaultProps = {
  range: [-10, 20]
}

export default ElectronicStructureOverview
