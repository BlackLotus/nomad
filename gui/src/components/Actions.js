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
import { makeStyles } from '@material-ui/core/styles'
import { Tooltip, IconButton, Button } from '@material-ui/core'
import clsx from 'clsx'

const useActionsStyles = makeStyles((theme) => ({
  root: {
    display: 'flex',
    width: '100%',
    boxSizing: 'border-box',
    alignItems: 'center'
  },
  spacer: {
    flexGrow: 1
  }
}))
export const Actions = React.memo(({
  header,
  justifyContent,
  className,
  classes,
  children
}) => {
  const useDynamicStyles = makeStyles((theme) => ({
    root: {
      justifyContent: justifyContent
    }
  }))
  const styles = useActionsStyles({classes: classes})
  const dynamicStyles = useDynamicStyles()

  return <div className={clsx(className, styles.root, dynamicStyles.root)}>
    {header}
    {header && <div className={styles.spacer}></div>}
    {children}
  </div>
})

Actions.propTypes = {
  header: PropTypes.any, // A text message or component to display at the left side of the actions
  justifyContent: PropTypes.string, // The flexbox justification of buttons
  className: PropTypes.string,
  classes: PropTypes.object,
  children: PropTypes.node
}

Actions.defaultProps = {
  justifyContent: 'flex-end'
}

const useActionStyles = makeStyles((theme) => ({
  root: {
    marginRight: theme.spacing(1),
    '&:last-child': {
      marginRight: 0
    }
  }
}))
export const Action = React.memo(({
  variant,
  color,
  size,
  href,
  disabled,
  onClick,
  tooltip,
  className,
  classes,
  children
}) => {
  const styles = useActionStyles({classes: classes})

  return <Tooltip title={tooltip || ''}>
    {variant === 'icon'
      ? <IconButton
        color={color}
        size={size}
        className={clsx(className, styles.root)}
        onClick={onClick}
        disabled={disabled}
        href={href}
        aria-label={tooltip}
      >
        {children}
      </IconButton>
      : <Button
        color={color}
        variant={variant}
        size={size}
        className={clsx(className, styles.root)}
        onClick={onClick}
        disabled={disabled}
        href={href}
        aria-label={tooltip}
      >
        {children}
      </Button>
    }
  </Tooltip>
})

Action.propTypes = {
  variant: PropTypes.string, // The variant of the MUI buttons
  color: PropTypes.string, // The color of the MUI buttons
  size: PropTypes.string, // Size of the MUI buttons
  href: PropTypes.string,
  disabled: PropTypes.bool,
  onClick: PropTypes.func,
  tooltip: PropTypes.string,
  className: PropTypes.string,
  classes: PropTypes.object,
  children: PropTypes.node
}

Action.defaultProps = {
  size: 'small',
  variant: 'icon'
}
