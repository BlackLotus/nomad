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
import React, {useMemo, useContext, useCallback, useState} from 'react'
import PropTypes from 'prop-types'
import clsx from 'clsx'
import {
  makeStyles,
  Typography,
  Tooltip,
  IconButton,
  TableBody,
  TableContainer,
  TableHead,
  Table,
  TableRow,
  TableCell
} from '@material-ui/core'
import ClipboardIcon from '@material-ui/icons/Assignment'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import _ from 'lodash'
import searchQuantities from '../searchQuantities'
import Placeholder from './visualization/Placeholder'
import NoData from './visualization/NoData'
import { formatNumber, serializeMetainfo } from '../utils'
import { Unit, toUnitSystem, useUnits } from '../units'

/**
 * Component for showing a metainfo quantity value together with a name and
 * description.
*/
const useQuantityStyles = makeStyles(theme => ({
  root: {
    maxWidth: 'fit-content'
  },
  valueContainer: {
    display: 'flex',
    alignItems: 'center',
    flexDirection: 'row',
    maxWidth: '100%'
  },
  value: {
    flexGrow: 1
  },
  ellipsis: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  ellipsisFront: {
    direction: 'rtl',
    textAlign: 'left'
  },
  valueAction: {},
  valueActionButton: {
    padding: 4
  },
  valueActionIcon: {
    fontSize: 16
  },
  row: {
    display: 'flex',
    flexWrap: 'wrap',
    flexDirection: 'row',
    '& > :not(:last-child)': {
      marginRight: theme.spacing(3)
    }
  },
  column: {
    display: 'flex',
    flexDirection: 'column',
    '& > :not(:first-child)': {
      marginTop: theme.spacing(1)
    }
  },
  flex: {
    display: 'flex',
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignContent: 'flex-start',
    '& div': {
      marginRight: theme.spacing(1)
    }
  },
  label: {
    color: 'rgba(0, 0, 0, 0.54)',
    fontSize: '0.75rem',
    fontWeight: 500
  },
  quantityList: {
    display: 'flex',
    flexDirection: 'column'
  }
}))

const Quantity = React.memo(({
  quantity,
  label,
  description,
  loading,
  placeholder,
  typography,
  noWrap,
  noLabel,
  row,
  column,
  flex,
  data,
  withClipboard,
  ellipsisFront,
  hideIfUnavailable,
  children,
  format
}) => {
  const styles = useQuantityStyles()
  const units = useUnits()
  const [noToolTip, setNoToolTip] = useState(false)
  let content = null
  let clipboardContent = null

  let valueClassName = styles.value
  if (noWrap && ellipsisFront) {
    valueClassName = `${valueClassName} ${styles.ellipsisFront}`
  }

  // Determine the final value to show.
  let value
  if (!loading) {
    if (typeof quantity === 'string') {
      value = data && quantity && _.get(data, quantity)
      if (format) {
        value = serializeMetainfo(quantity, value, units)
      }
    } else if (children) {
    } else {
      try {
        value = quantity(data)
      } catch {
        value = undefined
      }
    }

    if (value === 'not processed') {
      value = 'unavailable'
    }

    if (value === 'unavailable') {
      value = ''
    }

    if ((!value && !children) && hideIfUnavailable) {
      return null
    }

    if (children && children.length !== 0) {
      content = children
    } else if (value || value === 0) {
      if (Array.isArray(value)) {
        value = value.join(', ')
      }
      clipboardContent = value
      content = <Typography noWrap={noWrap} variant={typography} className={valueClassName}>
        {value}
      </Typography>
    } else {
      content = <Typography noWrap={noWrap} variant={typography} className={valueClassName}>
        <i>{placeholder || 'unavailable'}</i>
      </Typography>
    }
  }

  const def = typeof quantity === 'string'
    ? searchQuantities[quantity]
    : undefined

  // Determine the final label to show
  const useLabel = useMemo(() => {
    let useLabel = label
    if (!useLabel) {
      if (def?.name) {
        useLabel = def.name.replace(/_/g, ' ')
      } else if (typeof quantity === 'string') {
        useLabel = quantity
      } else {
        useLabel = 'MISSING LABEL'
      }
    }
    return useLabel
  }, [quantity, label, def])

  const handleClipboardTooltipOpen = useCallback((event, value) => {
    setNoToolTip(true)
  }, [setNoToolTip])

  const handleClipboardTooltipClose = useCallback((event, value) => {
    setNoToolTip(false)
  }, [setNoToolTip])

  const tooltip = (noToolTip ? '' : description || def?.description || '')

  if (row || column || flex) {
    return <div className={row ? styles.row : (column ? styles.column : styles.flex)}>{children}</div>
  } else {
    return (
      <Tooltip title={tooltip}>
        <div className={styles.root}>
          {!noLabel ? <Typography
            noWrap
            classes={{root: styles.label}}
            variant="caption"
          >{useLabel}</Typography> : ''}
          <div className={styles.valueContainer}>
            {loading
              ? <Typography noWrap={noWrap} variant={typography} className={valueClassName}>
                <i>loading ...</i>
              </Typography>
              : content
            }
            {withClipboard
              ? <CopyToClipboard
                className={styles.valueAction}
                text={clipboardContent}
                onCopy={() => null}
              >
                <Tooltip onClose={handleClipboardTooltipClose} onOpen={handleClipboardTooltipOpen} title={`Copy ${useLabel} to clipboard`}>
                  <div>
                    <IconButton
                      disabled={!clipboardContent}
                      classes={{root: styles.valueActionButton}}
                    >
                      <ClipboardIcon classes={{root: styles.valueActionIcon}}/>
                    </IconButton>
                  </div>
                </Tooltip>
              </CopyToClipboard>
              : ''
            }
          </div>
        </div>
      </Tooltip>
    )
  }
})

Quantity.propTypes = {
  children: PropTypes.node,
  label: PropTypes.string,
  typography: PropTypes.string,
  loading: PropTypes.bool,
  placeholder: PropTypes.string,
  noWrap: PropTypes.bool,
  noLabel: PropTypes.bool,
  row: PropTypes.bool,
  column: PropTypes.bool,
  flex: PropTypes.bool,
  data: PropTypes.object,
  quantity: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.func
  ]),
  withClipboard: PropTypes.bool,
  ellipsisFront: PropTypes.bool,
  hideIfUnavailable: PropTypes.bool,
  description: PropTypes.string,
  format: PropTypes.bool
}

export default Quantity

/**
 * Representational component for tables containing metainfo data.
 */
const useTableStyles = makeStyles(theme => ({
  root: {
    border: `1px solid ${theme.palette.grey[300]}`
  }
}))
export const MetaInfoTable = React.memo(({data, className, classes, children}) => {
  const styles = useTableStyles(classes)
  return <TableContainer className={clsx(className, styles.root)}>
    <Table size="small">
      {children}
    </Table>
  </TableContainer>
})
MetaInfoTable.propTypes = {
  data: PropTypes.object,
  className: PropTypes.string,
  classes: PropTypes.object,
  children: PropTypes.node
}

/**
 * Used to organize individual quantities in a table.
 */
const quantityTableContext = React.createContext()
export const QuantityTable = React.memo(({data, className, children}) => {
  return <quantityTableContext.Provider value={data}>
    <MetaInfoTable className={className}>
      <TableBody>
        {children}
      </TableBody>
    </MetaInfoTable>
  </quantityTableContext.Provider>
})
QuantityTable.propTypes = {
  data: PropTypes.object,
  className: PropTypes.string,
  children: PropTypes.node
}

/**
 * Used to organize Quantities in a table row.
 */
const useRowStyles = makeStyles(theme => ({
  root: {}
}))
export const QuantityRow = React.memo(({className, classes, children}) => {
  const styles = useRowStyles()

  return <TableRow className={clsx(className, styles.root)}>
    {children}
  </TableRow>
})

QuantityRow.propTypes = {
  className: PropTypes.string,
  classes: PropTypes.object,
  children: PropTypes.node
}

/**
 * Used to display a quantity in a table cell.
 */
export const QuantityCell = React.memo(({
  quantity,
  label,
  description,
  classes,
  className,
  children,
  ...other
}) => {
  const data = useContext(quantityTableContext)

  return <TableCell align="left" {...other}>
    {children || <Quantity
      quantity={quantity}
      label={label}
      description={description}
      format
      noWrap
      data={data}
    />}
  </TableCell>
})

QuantityCell.propTypes = {
  quantity: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  label: PropTypes.string,
  description: PropTypes.string,
  options: PropTypes.object,
  className: PropTypes.string,
  classes: PropTypes.object,
  children: PropTypes.node
}

/**
 * Used to display data from one or many sections in a table.
 */
const useStyles = makeStyles(theme => ({
  root: {
    width: '100%',
    height: '100%'
  },
  table: {
    marginBottom: theme.spacing(1)
  }
}))
export const SectionTable = React.memo(({
  data,
  section,
  quantities,
  horizontal,
  classes,
  className,
  units,
  'data-testid': testID
}) => {
  const styles = useStyles({classes: classes})

  // If data is set explicitly to False, we show the NoData component.
  let content
  if (data === false) {
    content = <NoData data-testid={`${testID}-nodata`}/>
  } else if (!data) {
    content = <Placeholder variant="rect" data-testid={`${testID}-placeholder`}/>
  } else {
    content = <MetaInfoTable className={styles.table}>
      <TableHead>
        {horizontal
          ? <TableRow>
            {Object.keys(quantities).map((key, index) => {
              const defCustom = quantities[key]
              const def = searchQuantities[`${section}.${key}`]
              const unitName = defCustom.unit || def?.unit
              const unit = unitName && new Unit(unitName)
              const unitLabel = unit && unit.label(units)
              const description = defCustom.description || def.description || ''
              const content = unit ? `${defCustom.label} (${unitLabel})` : defCustom.label
              const align = defCustom.align || 'right'
              return <TableCell key={index} align={align}>
                <Tooltip title={description}>
                  <span>
                    {content}
                  </span>
                </Tooltip>
              </TableCell>
            })}
          </TableRow>
          : null
        }
      </TableHead>
      <TableBody>
        {horizontal
          ? <>{data.data.map((row, i) => (
            <TableRow key={i}>
              {Object.keys(quantities).map((key, j) => {
                const defCustom = quantities[key]
                const def = searchQuantities[`${section}.${key}`]
                const unit = defCustom.unit || def?.unit
                const dtype = defCustom?.type?.type_data || def?.type?.type_data
                const align = defCustom.align || 'right'
                let value = row[key]
                if (value !== undefined) {
                  if (!isNaN(value)) {
                    value = formatNumber(
                      unit ? toUnitSystem(value, unit, units, false) : value,
                      dtype
                    )
                  }
                } else {
                  value = defCustom.placeholder || 'unavailable'
                }
                return <TableCell key={j} align={align}>{value}</TableCell>
              })}
            </TableRow>
          ))}</>
          : <>{Object.keys(quantities).map((key, i) => (
            <TableRow key={i}>
              {data.data.map((row, j) => {
                const defCustom = quantities[key]
                const def = searchQuantities[`${section}.${key}`]
                const unitName = defCustom.unit || def?.unit
                const unit = unitName && new Unit(unitName)
                const unitLabel = unit ? ` ${unit.label(units)}` : ''
                const description = defCustom.description || def.description || ''
                const dtype = defCustom?.type?.type_data || def?.type?.type_data
                const align = defCustom.align || 'right'
                let value = row[key]
                if (value !== undefined) {
                  if (!isNaN(value)) {
                    value = `${formatNumber(
                      unit ? toUnitSystem(value, unit, units, false) : value,
                      dtype
                    )}${unitLabel}`
                  }
                } else {
                  value = defCustom.placeholder || 'unavailable'
                }
                return <>
                  <TableCell key={j} align={align}>
                    <Tooltip title={description}>
                      <span>
                        {defCustom.label}
                      </span>
                    </Tooltip>
                  </TableCell>
                  <TableCell key={j} align={align}>{value}</TableCell>
                </>
              })}
            </TableRow>
          ))}</>
        }
      </TableBody>
    </MetaInfoTable>
  }

  return <div className={clsx(className, styles.root)} data-testid={testID}>
    {content}
  </div>
})

SectionTable.propTypes = {
  data: PropTypes.oneOfType([
    PropTypes.bool, // Set to False to show NoData component
    PropTypes.shape({
      data: PropTypes.arrayOf(PropTypes.object).isRequired
    })
  ]),
  section: PropTypes.string,
  quantities: PropTypes.any,
  horizontal: PropTypes.bool,
  className: PropTypes.string,
  classes: PropTypes.object,
  units: PropTypes.object,
  'data-testid': PropTypes.string
}
