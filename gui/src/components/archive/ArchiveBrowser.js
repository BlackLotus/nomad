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
import React, { useMemo } from 'react'
import PropTypes from 'prop-types'
import { atom, useRecoilState, useRecoilValue } from 'recoil'
import { Box, FormGroup, FormControlLabel, Checkbox, TextField, Typography, makeStyles, Tooltip } from '@material-ui/core'
import { useRouteMatch, useHistory } from 'react-router-dom'
import Autocomplete from '@material-ui/lab/Autocomplete'
import Browser, { Item, Content, Compartment, List, Adaptor, formatSubSectionName } from './Browser'
import { resolveRef, rootSections } from './metainfo'
import { Title, metainfoAdaptorFactory, DefinitionLabel } from './MetainfoBrowser'
import { Matrix, Number } from './visualizations'
import Markdown from '../Markdown'
import { Overview } from './Overview'
import { toUnitSystem, useUnits } from '../../units'

export const configState = atom({
  key: 'config',
  default: {
    'showMeta': false,
    'showCodeSpecific': false,
    'showAllDefined': false
  }
})

export default function ArchiveBrowser({data}) {
  const searchOptions = useMemo(() => archiveSearchOptions(data), [data])

  // For some reason, this hook does not work in all of the components used in
  // the Browser (notably: Quantity, QuantityItemPreview). In order to pass the
  // up-to-date unit information, we pass the hook value down the component
  // hierarchy.
  const units = useUnits()
  return (
    <Browser
      adaptor={archiveAdaptorFactory(data, undefined, units)}
      form={<ArchiveConfigForm searchOptions={searchOptions} />}
    />
  )
}
ArchiveBrowser.propTypes = ({
  data: PropTypes.object.isRequired
})

function ArchiveConfigForm({searchOptions}) {
  const [config, setConfig] = useRecoilState(configState)

  const handleConfigChange = event => {
    const changes = {[event.target.name]: event.target.checked}
    if (changes.showCodeSpecific) {
      changes.showAllDefined = !changes.showCodeSpecific
    } else if (changes.showAllDefined) {
      changes.showCodeSpecific = !changes.showAllDefined
    }
    setConfig({...config, ...changes})
  }

  const history = useHistory()
  const { url } = useRouteMatch()

  return (
    <Box marginTop={-3} padding={0}>
      <FormGroup row style={{alignItems: 'center'}}>
        <Box style={{width: 350, height: 60}}>
          <Autocomplete
            options={searchOptions}
            getOptionLabel={(option) => option.name}
            style={{ width: 350, marginTop: -20 }}
            onChange={(_, value) => {
              if (value) {
                history.push(url + value.path)
              }
            }}
            renderInput={(params) => <TextField {...params} label="search" margin="normal" />}
          />
        </Box>
        <Box flexGrow={1} />
        <Tooltip title="Enable to also show all code specific data">
          <FormControlLabel
            control={
              <Checkbox
                checked={config.showCodeSpecific}
                onChange={handleConfigChange}
                name="showCodeSpecific"
              />
            }
            label="code specific"
          />
        </Tooltip>
        <Tooltip title="Enable to also show metadata that is in principle available, but not within this entry">
          <FormControlLabel
            control={
              <Checkbox
                checked={config.showAllDefined}
                onChange={handleConfigChange}
                name="showAllDefined"
              />
            }
            label="all defined"
          />
        </Tooltip>
        <Tooltip title="Show the Metainfo definition on the bottom of each lane">
          <FormControlLabel
            control={
              <Checkbox
                checked={config.showMeta}
                onChange={handleConfigChange}
                name="showMeta" />
            }
            label="definitions"
          />
        </Tooltip>
      </FormGroup>
    </Box>
  )
}
ArchiveConfigForm.propTypes = ({
  searchOptions: PropTypes.arrayOf(PropTypes.object).isRequired
})

function archiveAdaptorFactory(data, sectionDef, units) {
  return new SectionAdaptor(data, sectionDef || rootSections.find(def => def.name === 'EntryArchive'), undefined, {archive: data}, units)
}

function archiveSearchOptions(data) {
  const options = []
  const optionDefs = {}
  const optionKeys = {}
  function traverse(data, def, parentPath) {
    for (let key in data) {
      const childDef = def._properties[key]
      if (!childDef) {
        continue
      }

      const child = data[key]
      if (!child) {
        continue
      }

      let path = `${parentPath}/${key}`
      if (childDef.m_def === 'SubSection') {
        const sectionDef = resolveRef(childDef.sub_section)
        if (Array.isArray(child) && child.length > 0 && child[0]) {
          if (child.length > 1) {
            child.forEach((value, index) => traverse(value, sectionDef, `${path}:${index}`))
          } else {
            traverse(child[0], sectionDef, path)
          }
        } else {
          traverse(child, sectionDef, path)
        }
      }

      if (optionDefs[childDef._qualifiedName]) {
        continue
      }
      optionDefs[childDef._qualifiedName] = childDef

      const option = {
        name: key,
        data: data,
        def: childDef,
        path: path
      }
      options.push(option)

      if (optionKeys[key]) {
        const addPath = option => {
          const parents = option.path.split('/')
          const parent = parents[parents.length - 2].replace(/:[0-9]+$/, '')
          option.name += ` (${parent})`
        }
        if (!optionKeys[key].name.includes('(')) {
          addPath(optionKeys[key])
        }
        addPath(option)
      } else {
        optionKeys[key] = option
      }
    }
  }
  traverse(data, rootSections.find(def => def.name === 'EntryArchive'), '')
  return options
}

class ArchiveAdaptor extends Adaptor {
  constructor(obj, def, parent, context, units) {
    super(obj)
    this.def = def
    this.parent = parent
    this.context = context
    this.units = units
  }

  adaptorFactory(obj, def, parent, context) {
    if (def.m_def === 'Section') {
      return new SectionAdaptor(obj, def, parent, context || this.context, this.units)
    } else if (def.m_def === 'Quantity') {
      return new QuantityAdaptor(obj, def, parent, context || this.context, this.units)
    }
  }

  itemAdaptor(key) {
    if (key === '_metainfo') {
      return metainfoAdaptorFactory(this.def)
    } else {
      throw new Error('Unknown item key')
    }
  }
}

class SectionAdaptor extends ArchiveAdaptor {
  itemAdaptor(key) {
    const [name, index] = key.split(':')
    const property = this.def._properties[name]
    const value = this.e[name]
    if (!property) {
      return super.itemAdaptor(key)
    } else if (property.m_def === 'SubSection') {
      const sectionDef = resolveRef(property.sub_section)
      if (property.repeats) {
        return this.adaptorFactory(value[parseInt(index || 0)], sectionDef, this.e)
      } else {
        return this.adaptorFactory(value, sectionDef, this.e)
      }
    } else if (property.m_def === 'Quantity') {
      // References: sections and quantities
      if (property.type.type_kind === 'reference') {
        if (property.shape.length === 0) {
          // some sections cannot be resolved, because they are not part of the archive
          // user_id->user is one example
          const resolved = resolveRef(value, this.context.archive) || {}
          const resolvedDef = resolveRef(property.type.type_data)
          if (resolvedDef.name === 'User' && !resolved.user_id) {
            resolved.user_id = value
          }
          return this.adaptorFactory(resolved, resolvedDef, this.e)
        } else {
        }
      }
      // Regular quantities
      return this.adaptorFactory(value, property, this.e)
    } else {
      throw new Error('Unknown metainfo meta definition')
    }
  }
  render() {
    return <Section section={this.e} def={this.def} parent={this.parent} units={this.units}/>
  }
}

class QuantityAdaptor extends ArchiveAdaptor {
  render() {
    return <Quantity value={this.e} def={this.def} units={this.units}/>
  }
}

function QuantityItemPreview({value, def, units}) {
  if (def.type.type_kind === 'reference') {
    return <Box component="span" fontStyle="italic">
      <Typography component="span">reference ...</Typography>
    </Box>
  }
  if (def.shape.length > 0) {
    const dimensions = []
    let current = value
    for (let i = 0; i < def.shape.length; i++) {
      dimensions.push(current.length)
      current = current[0]
    }
    let typeLabel
    if (def.type.type_kind === 'python') {
      typeLabel = 'list'
    } else {
      if (dimensions.length === 1) {
        typeLabel = 'vector'
      } else if (dimensions.length === 2) {
        typeLabel = 'matrix'
      } else {
        typeLabel = 'tensor'
      }
    }
    return <Box component="span" whiteSpace="nowrap" fontStyle="italic">
      <Typography component="span">
        {dimensions.map((dimension, index) => (
          <span key={index}>
            {index > 0 && <span>&nbsp;&times;&nbsp;</span>}{String(dimension)}
          </span>
        ))}&nbsp;{typeLabel}
      </Typography>
    </Box>
  } else {
    const val = (def.type.type_data === 'nomad.metainfo.metainfo._Datetime' ? new Date(value).toLocaleString() : value)
    const [finalValue, finalUnit] = def.unit
      ? toUnitSystem(val, def.unit, units, true)
      : [val, def.unit]
    return <Box component="span" whiteSpace="nowarp">
      <Number component="span" variant="body1" value={finalValue} exp={8} />
      {finalUnit && <Typography component="span">&nbsp;{finalUnit}</Typography>}
    </Box>
  }
}
QuantityItemPreview.propTypes = ({
  value: PropTypes.any,
  def: PropTypes.object.isRequired,
  units: PropTypes.object
})

function QuantityValue({value, def, units}) {
  const val = (def.type.type_data === 'nomad.metainfo.metainfo._Datetime' ? new Date(value).toLocaleString() : value)
  const [finalValue, finalUnit] = def.unit
    ? toUnitSystem(val, def.unit, units, true)
    : [val, def.unit]

  return <Box
    marginTop={2} marginBottom={2} textAlign="center" fontWeight="bold"
  >
    {def.shape.length > 0 ? <Matrix values={finalValue} shape={def.shape} invert={def.shape.length === 1} /> : <Number value={finalValue} exp={16} variant="body2" />}
    {def.shape.length > 0 &&
      <Typography noWrap variant="caption">
        ({def.shape.map((dimension, index) => <span key={index}>
          {index > 0 && <span>&nbsp;&times;&nbsp;</span>}{String(dimension)}
        </span>)}&nbsp;)
      </Typography>
    }
    {finalUnit && <Typography noWrap>{finalUnit}</Typography>}
  </Box>
}
QuantityValue.propTypes = ({
  value: PropTypes.any,
  def: PropTypes.object.isRequired,
  units: PropTypes.object
})

function Section({section, def, parent, units}) {
  const config = useRecoilValue(configState)

  if (!section) {
    console.error('section is not available')
    return ''
  }

  const filter = config.showCodeSpecific ? def => true : def => !def.name.startsWith('x_')
  let sub_sections = def.sub_sections
  if (def.name === 'EntryArchive') {
    // put the most abstract data (last added data) first, e.g. results, metadata, workflow, run
    sub_sections = [...def.sub_sections]
    sub_sections.reverse()
  }

  return <Content>
    <Title def={def} data={section} kindLabel="section" />
    <Overview section={section} def={def} units={units}/>
    <Compartment title="sub sections">
      {sub_sections
        .filter(subSectionDef => section[subSectionDef.name] || config.showAllDefined)
        .filter(filter)
        .map(subSectionDef => {
          const key = subSectionDef.name
          const disabled = section[key] === undefined
          if (!disabled && subSectionDef.repeats && section[key].length > 1) {
            return <List
              key={subSectionDef.name}
              itemKey={subSectionDef.name}
              title={formatSubSectionName(subSectionDef.name)} disabled={disabled}
            />
          } else {
            return <Item key={key} itemKey={key} disabled={disabled}>
              <Typography component="span">
                <Box fontWeight="bold" component="span">
                  {formatSubSectionName(subSectionDef.name)}
                </Box>
              </Typography>
            </Item>
          }
        })
      }
    </Compartment>
    <Compartment title="quantities">
      {def.quantities
        .filter(quantityDef => section[quantityDef.name] !== undefined || config.showAllDefined)
        .filter(filter)
        .map(quantityDef => {
          const key = quantityDef.name
          const disabled = section[key] === undefined
          return (
            <Item key={key} itemKey={key} disabled={disabled}>
              <Box component="span" whiteSpace="nowrap" style={{maxWidth: 100, overflow: 'ellipses'}}>
                <Typography component="span">
                  <Box fontWeight="bold" component="span">
                    {quantityDef.name}
                  </Box>
                </Typography>{!disabled &&
                  <span>&nbsp;=&nbsp;
                    <QuantityItemPreview
                      value={section[quantityDef.name]}
                      def={quantityDef}
                      units={units}
                    />
                  </span>
                }
              </Box>
            </Item>
          )
        })
      }
    </Compartment>
    <Meta def={def} />
  </Content>
}
Section.propTypes = ({
  section: PropTypes.object.isRequired,
  def: PropTypes.object.isRequired,
  parent: PropTypes.any,
  units: PropTypes.object
})

function Quantity({value, def, units}) {
  return <Content>
    <Title def={def} data={value} kindLabel="value" />
    <QuantityValue
      value={value}
      def={def}
      units={units}
    />
    <Meta def={def} />
  </Content>
}
Quantity.propTypes = ({
  value: PropTypes.any,
  def: PropTypes.object.isRequired,
  units: PropTypes.object
})

const useMetaStyles = makeStyles(theme => ({
  description: {
    marginTop: theme.spacing(1)
  },
  graph: {
    marginTop: theme.spacing(3)
  },
  metainfo: {
    marginBottom: theme.spacing(2)
  },
  metainfoItem: {
    fontWeight: 'bold'
  }
}))
export function Meta({def}) {
  const classes = useMetaStyles()
  const config = useRecoilValue(configState)
  if (!config.showMeta) {
    return ''
  }
  return <Compartment title="meta" color="primary">
    <div className={classes.metainfo}>
      <Item itemKey="_metainfo">
        <DefinitionLabel classes={{root: classes.metainfoItem}} def={def} isDefinition component="span" />
      </Item>
    </div>
    <Markdown classes={{root: classes.description}}>{def.description}</Markdown>
  </Compartment>
}
Meta.propTypes = ({
  def: PropTypes.object
})
