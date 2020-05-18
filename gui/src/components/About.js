import React, { useContext, useLayoutEffect, useRef, useCallback, useEffect } from 'react'
import {ReactComponent as AboutSvg} from './about.svg'
import PropTypes from 'prop-types'
import Markdown from './Markdown'
import { appBase, optimadeBase, apiBase, debug, consent } from '../config'
import { apiContext } from './api'
import packageJson from '../../package.json'
import { domains } from './domains'
import { Grid, Card, CardContent, Typography, makeStyles, Link } from '@material-ui/core'
import { Link as RouterLink, useHistory } from 'react-router-dom'

export const CodeList = () => {
  const {info} = useContext(apiContext)

  if (!info) {
    return '...'
  }

  return info.codes.reduce((result, code, index) => {
    if (index !== 0) {
      result.push(', ')
    }
    if (code.code_homepage) {
      result.push(<Link target="external" key={code.code_name} href={code.code_homepage}>{code.code_name}</Link>)
    } else {
      result.push(code.code_name)
    }
    return result
  }, [])
}

const useCardStyles = makeStyles(theme => ({
  title: {
    marginBottom: theme.spacing(1)
  }
}))

function InfoCard({title, children, xs, top, bottom}) {
  const classes = useCardStyles()
  const style = {}
  if (top) {
    style['paddingBottom'] = 0
  }
  if (bottom) {
    style['paddingTop'] = 0
  }
  return <Grid item xs={xs} style={style}>
    <Card>
      <CardContent>
        <Typography variant="h6" className={classes.title}>{title}</Typography>
        <Typography component="div">{children}</Typography>
      </CardContent>
    </Card>
  </Grid>
}
InfoCard.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  xs: PropTypes.number,
  top: PropTypes.bool,
  bottom: PropTypes.bool
}

const useStyles = makeStyles(theme => ({
  root: {
    padding: theme.spacing(3)
  },
  container: {
    maxWidth: 1024,
    margin: 'auto',
    width: '100%'
  }
}))

export default function About() {
  const classes = useStyles()
  const {info} = useContext(apiContext)
  const svg = useRef()
  const history = useHistory()

  const makeClickable = useCallback((id, onClick) => {
    const element = svg.current.querySelector('#' + id)
    element.style.cursor = 'pointer'
    element.firstChild.onclick = () => {
      onClick()
    }
  }, [svg])

  const setText = useCallback((id, lines) => {
    const element = svg.current.querySelector('#' + id)
    const x = element.getAttribute('x')
    element.innerHTML = lines.map((line, i) => `<tspan x="${x}" dy="${i === 0 ? '0' : '1.2em'}">${line}</tspan>`).join('')
  }, [svg])

  useLayoutEffect(() => {
    makeClickable('upload', () => {
      history.push('/upload')
    })
    makeClickable('encyclopedia', () => {
      window.location.href = 'https://encyclopedia.nomad-coe.eu/gui/#/search'
    })
    makeClickable('search', () => {
      history.push('/search')
    })
  }, [svg])

  useEffect(() => {
    const statistics = (info && info.statistics) || {}
    const value = (key, unit) => {
      const nominal = statistics[key]
      let stringValue = null
      if (nominal) {
        if (nominal >= 1.0e+9) {
          stringValue = Math.floor(nominal / 1.0e+9) + ' bln.'
        } else if (nominal >= 1.0e+6) {
          stringValue = Math.floor(nominal / 1.0e+6) + ' mln.'
        } else {
          stringValue = Math.floor(nominal / 1.0e+3) + ' tsd.'
        }
        return `${stringValue || '...'} ${unit}`
      } else {
        return '...'
      }
    }
    setText('repositoryStats', [
      value('n_entries', 'entries'),
      value('n_uploads', 'uploads')
    ])
    setText('archiveStats', [
      value('n_calculations', 'results'),
      value('n_quantities', 'quantities')
    ])
  }, [svg, info])

  return <div className={classes.root}>
    <Grid className={classes.container} container spacing={2}>
      <Grid item xs={12}>
        <Markdown>{`
        # The NOMAD Repository and Archive

        This is the *graphical user interface* (GUI) for the NOMAD Repository and
        Archive. It allows you to **search, access, and download all NOMAD data** in its
        raw (Repository) and processed (Archive) form. You can **upload and manage your own
        raw materials science data**. Learn more about what data can be uploaded
        and how to prepare your data on the [NOMAD Repository homepage](https://repository.nomad-coe.eu/).
        You can access all published data without an account. If you want to provide
        your own data, please login or register for an account.
        `}</Markdown>
      </Grid>
      <InfoCard xs={6} title="Interactive Search" top>
        NOMAD extracts <b>rich metadata</b> from uploaded raw-data. <Link component={RouterLink} to={'/search'}>
        Explore NOMAD&apos;s data</Link> by creating complex queries from interactive data visualizations of key
        properties, including the simulated composition/system, used method, upload metadata,
        as well as material classifications and available quantities. Or use
        the <b>Optimade</b> filter language to add arbitrarily nested queries.
      </InfoCard>
      <InfoCard xs={6} title="A common data format" top>
        The <b>NOMAD Archive</b> provides data in processed and normalized form in a machine processable and common hierarchical format.
        All data in the NOMAD Archive is organized into nested sections of quantities with well defined units,
        data types, shapes, and descriptions. These definitions are called the <b>NOMAD Metainfo</b> and they
        can be <Link component={RouterLink} to={'/metainfo'}>browsed here</Link>.
      </InfoCard>
      <Grid item xs={12} style={{paddingTop: 0, paddingBottom: 0}}>
        <AboutSvg ref={svg}></AboutSvg>
      </Grid>
      <InfoCard xs={4} title="Uploading is simple" bottom>
        <p>
        You provide your own data <i>as is</i>. Just zip your code input and out files as they are,
        including nested directory structures and potential auxiliary files, and upload
        up to 32GB in a single .zip or .tar(.gz) file. NOMAD will automatically discover
        and process the relevant files.
        </p>
        <p>
        You can <b>privately</b> inspect, curate, or delete your data before publishing.
        Data can be published with an <b>embargo (up to 3 years)</b> to only share data with
        selected users.
        </p>
        <p>
        Add additional metadata like <b>comments</b>, <b>references</b> to websites or papers, and your
          <b>co-authors</b>. Curate your uploaded code runs into larger <b>datasets</b> and cite your data with a <b>DOI</b>
        that we provide on request.
        </p>
        <p>
          You can provide via GUI or shell command <Link component={RouterLink} to={'/uploads'}>here</Link>.
          Manage already uploaded data <Link component={RouterLink} to={'/userdata'}>here</Link>.
        </p>
      </InfoCard>
      <InfoCard xs={4} title="Processing" bottom>
        <p>
        Uploaded data is automatically processed and made available
        in the uploaded <b>raw files</b> or in its processed and unified <b>Archive</b> form.
        NOMAD parsers convert raw code input and output files into NOMAD&apos;s common data format.
        You can inspect the Archive form and extracted metadata before
        publishing your data.
        </p>
        <p>NOMAD supports most community codes: <CodeList/></p>
        <p>
        To use NOMAD&apos;s parsers and normalizers outside of NOMAD.
        Read <Link href="">here</Link> on how to install
        our software and how to use NOMAD processing in your Python environment.
        </p>
      </InfoCard>
      <InfoCard xs={4} title="APIs" bottom><Markdown>{`
      The NOMAD can also be accessed programmatically via ReST APIs.
      There is the proprietary NOMAD API and an implementation of the
      standardized [OPTiMaDe API (0.10.0)](https://github.com/Materials-Consortia/OPTiMaDe/tree/master)
      materials science database API.

      Both APIs are described via [swagger/OpenAPI spec.](https://swagger.io/),
      therefore you can use your favorite swagger client library
      (e.g. [bravado](https://github.com/Yelp/bravado) for Python):
      - [NOMAD API](${apiBase}/)
      - [OPTiMaDe API](${optimadeBase}/)

      There is a [tutorial on how to use the API with plain Python](${appBase}/docs/api_tutorial.html).
      Another [tutorial covers how to install and use NOMAD's Python client library](${appBase}/docs/archive_tutorial.html).
      The [NOMAD Analytics Toolkit](https://analytic-toolkit.nomad-coe.eu) allows to use
      this without installation and directly on NOMAD servers.
      `}</Markdown></InfoCard>
      <Grid item xs={12}>
        <Markdown>{`
        ### Getting Help
        If you encounter any difficulties, please write to
        [webmaster@nomad-coe.eu](mailto:webmaster@nomad-coe.eu). If you think
        that this web-page is not working as expected, or if you want to start a discussion
        about possible features, feel free to open an issue on our [issue tracking
        system](https://gitlab.mpcdf.mpg.de/nomad-lab/nomad-FAIR/issues).

        ### Developer Documentation
        The [in-depth documentation](${appBase}/docs/index.html)
        contains a general introduction to NOMAD and its underlying architecture,
        more information and tutorials, how to prepare uploads, how
        to use the API, developer information, how to operate your own NOMAD (a so called
        Oasis), how to contribute parsers, and much more.

        ### Source code
        The source-code for the NOMAD Repository and Archive is maintained
        at the MPCDF's [gitlab](https://gitlab.mpcdf.mpg.de/nomad-lab/nomad-FAIR).
        To push code, you need an MPCDF account and you can apply
        [here](https://www.mpcdf.mpg.de/userspace/forms/onlineregistrationform).

        ${debug ? `
        ### Material science data and domains
        Originally NOMAD was build for DFT calculations and data from the respective
        community code. By NOMAD supports multiple materials science domains:

        ${info && info.domains.map(domain => domains[domain.name]).map(domain => `- ${domain.name}: ${domain.about}`).join('\n')}
        ` : ''}

        ${debug ? `
        ### Log management with Elastic stack
        We use a central logging system based on the *elastic*-stack
        (previously called *Elastic Logstash Kibana* (ELK)-stack).
        This system pushes logs, events, monitoring data,
        and other application metrics to a central database where it
        can be analysed visually by us.

        ### Test user
        During development this GUI might not be connected to the actual NOMAD
        repository. Therefore, you cannot create a user or login with an existing
        user. You might use the test user \`leonard.hofstadter@nomad-fairdi.tests.de\`
        with password \`password\`. The user \`sheldon.cooper@nomad-fairdi.tests.de\` is
        used for data that has no provenance with the original NOMAD CoE database.
        ` : ''}

        ### Terms of use and licenses
        ${consent}

        ### About this version
        - version (API): \`${info ? info.version : 'loading'}/${info ? info.git.commit : 'loading'}\`
        - version (GUI): \`${packageJson.version}/${packageJson.commit}\`
        - domains: ${info ? Object.keys(info.domains).map(domain => info.domains[domain].name).join(', ') : 'loading'}
        - git: \`${info ? info.git.ref : 'loading'}; ${info ? info.git.version : 'loading'}\`
        - last commit message: *${info ? info.git.log : 'loading'}*
        - supported codes: ${info ? info.codes.join(', ') : 'loading'}
        - parsers: ${info ? info.parsers.join(', ') : 'loading'}
        - normalizers: ${info ? info.normalizers.join(', ') : 'loading'}
      `}</Markdown>
      </Grid>
    </Grid>
  </div>
}
