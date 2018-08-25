import React, { Component } from 'react'
import HtmlToReact from 'html-to-react'
import { withRouter } from 'react-router-dom';
import { HashLink as Link } from 'react-router-hash-link';

const processNodeDefinitions = new HtmlToReact.ProcessNodeDefinitions(React)
const processingInstructions = [
  {
    shouldProcessNode: node => node.type === 'tag' && node.name === 'a' && node.attribs['href'],
    processNode: (node, children) => (<Link smooth to={`/documentation/${node.attribs['href']}`}>{children}</Link>)
  },
  {
    shouldProcessNode: node => true,
    processNode: processNodeDefinitions.processDefaultNode
  }
]
const isValidNode = () => true
const htmlToReactParser = new HtmlToReact.Parser();
const domParser = new DOMParser()

class Documentation extends Component {
  state = {
    react: ''
  }

  onRouteChanged() {
    const fetchAndUpdate = path => {
      fetch(`/docs/${path}`)
        .then(response => response.text())
        .then(content => {
          // extract body of html page
          const doc = domParser.parseFromString(content, "application/xml")
          const bodyHtml = doc.getElementsByTagName('body')[0].innerHTML

          // replace a hrefs with Link to
          const react = htmlToReactParser.parseWithInstructions(bodyHtml, isValidNode, processingInstructions)

          this.setState({
            react: react
          })
        })
        .catch(err => {
          if (path !== 'index.html') {
            fetchAndUpdate('index.html')
          } else {
            console.error(err)
          }
        })
    }
    const path = this.props.location.pathname.replace('/documentation/', '')
    fetchAndUpdate(path)
  }

  componentDidUpdate(prevProps) {
    if (this.props.location !== prevProps.location) {
      this.onRouteChanged()
    }
  }

  componentWillMount() {
    this.onRouteChanged()
  }

  render() {
    return this.state.react
  }
}

export default withRouter(Documentation)