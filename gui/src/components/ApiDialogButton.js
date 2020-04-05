import React from 'react'
import PropTypes from 'prop-types'
import { withStyles, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, Button, Tooltip, Typography } from '@material-ui/core'
import CodeIcon from '@material-ui/icons/Code'
import ReactJson from 'react-json-view'
import Markdown from './Markdown'
import { CopyToClipboard } from 'react-copy-to-clipboard'
import ClipboardIcon from '@material-ui/icons/Assignment'

class ApiDialogUnstyled extends React.Component {
  static propTypes = {
    classes: PropTypes.object.isRequired,
    data: PropTypes.any.isRequired,
    title: PropTypes.string,
    onClose: PropTypes.func
  }

  static styles = (theme) => ({
    content: {
      paddingBottom: 0
    },
    json: {
      marginTop: theme.spacing.unit * 2,
      marginBottom: theme.spacing.unit * 2
    },
    codeContainer: {
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'flex-start'
    },
    code: {
      flexGrow: 1,
      marginRight: theme.spacing.unit,
      overflow: 'hidden'
    },
    codeActions: {
      marginTop: theme.spacing.unit * 3
    }
  })

  render() {
    const { classes, title, data, onClose, ...dialogProps } = this.props

    return (
      <Dialog maxWidth="lg" fullWidth {...dialogProps}>
        <DialogTitle>{title || 'API Code'}</DialogTitle>

        <DialogContent classes={{root: classes.content}}>
          <Typography>Access the archive as JSON via <i>curl</i>:</Typography>
          <div className={classes.codeContainer}>
            <div className={classes.code}>
              <Markdown>{`
                \`\`\`
                  ${data.curl}
                \`\`\`
              `}</Markdown>
            </div>
            <div className={classes.codeActions}>
              <CopyToClipboard text={data.curl} onCopy={() => null}>
                <Tooltip title="Copy to clipboard">
                  <IconButton>
                    <ClipboardIcon />
                  </IconButton>
                </Tooltip>
              </CopyToClipboard>
            </div>
          </div>

          <Typography>Access the archive in <i>python</i>:</Typography>
          <div className={classes.codeContainer}>
            <div className={classes.code}>
              <Markdown>{`
                \`\`\`
                  ${data.python}
                \`\`\`
              `}</Markdown>
            </div>
            <div className={classes.codeActions}>
              <CopyToClipboard text={data.python} onCopy={() => null}>
                <Tooltip title="Copy to clipboard">
                  <IconButton>
                    <ClipboardIcon />
                  </IconButton>
                </Tooltip>
              </CopyToClipboard>
            </div>
          </div>

          <Typography>The repository API response as JSON:</Typography>
          <div className={classes.codeContainer}>
            <div className={classes.code}>
              <div className={classes.json}>
                <ReactJson
                  src={data}
                  enableClipboard={false}
                  collapsed={2}
                  displayObjectSize={false}
                />
              </div>
            </div>
            <div className={classes.codeActions}>
              <CopyToClipboard text={data} onCopy={() => null}>
                <Tooltip title="Copy to clipboard">
                  <IconButton>
                    <ClipboardIcon />
                  </IconButton>
                </Tooltip>
              </CopyToClipboard>
            </div>
          </div>
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    )
  }
}

export const ApiDialog = withStyles(ApiDialogUnstyled.styles)(ApiDialogUnstyled)

class ApiDialogButtonUnstyled extends React.Component {
  static propTypes = {
    classes: PropTypes.object.isRequired,
    data: PropTypes.any.isRequired,
    title: PropTypes.string,
    component: PropTypes.func
  }

  static styles = theme => ({
    root: {}
  })

  state = {
    showDialog: false
  }

  constructor(props) {
    super(props)
    this.handleShowDialog = this.handleShowDialog.bind(this)
  }

  handleShowDialog() {
    this.setState({showDialog: !this.state.showDialog})
  }

  render() {
    const { classes, component, ...dialogProps } = this.props
    const { showDialog } = this.state

    return (
      <div className={classes.root}>
        {component ? component({onClick: this.handleShowDialog}) : <Tooltip title="Show API code">
          <IconButton onClick={this.handleShowDialog}>
            <CodeIcon />
          </IconButton>
        </Tooltip>
        }
        <ApiDialog
          {...dialogProps} open={showDialog}
          onClose={() => this.setState({showDialog: false})}
        />
      </div>
    )
  }
}

export default withStyles(ApiDialogButtonUnstyled.styles)(ApiDialogButtonUnstyled)
