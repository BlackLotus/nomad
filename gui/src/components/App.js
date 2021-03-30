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
import { Router, Route } from 'react-router-dom'
import { QueryParamProvider } from 'use-query-params'
import history from '../history'
import PiwikReactRouter from 'piwik-react-router'
import { nomadTheme, matomoEnabled, matomoUrl, matomoSiteId, keycloakBase, keycloakRealm,
  keycloakClientId } from '../config'
import Keycloak from 'keycloak-js'
import { KeycloakProvider } from 'react-keycloak'
import { MuiThemeProvider } from '@material-ui/core/styles'
import { ApiProvider } from './api'
import { ErrorSnacks, ErrorBoundary } from './errors'
import Navigation from './nav/Navigation'

export const matomo = matomoEnabled ? PiwikReactRouter({
  url: matomoUrl,
  siteId: matomoSiteId,
  clientTrackerName: 'stat.js',
  serverTrackerName: 'stat'
}) : []

// matomo.push('requireConsent')

const keycloak = Keycloak({
  url: keycloakBase,
  realm: keycloakRealm,
  clientId: keycloakClientId
})

export default function App() {
  return (
    <KeycloakProvider keycloak={keycloak} initConfig={{ onLoad: 'check-sso', 'checkLoginIframe': false }} LoadingComponent={<div />}>
      <Router history={matomoEnabled ? matomo.connectToHistory(history) : history}>
        <QueryParamProvider ReactRouterRoute={Route}>
          <MuiThemeProvider theme={nomadTheme}>
            <ErrorSnacks>
              <ErrorBoundary>
                <ApiProvider>
                  <Navigation />
                </ApiProvider>
              </ErrorBoundary>
            </ErrorSnacks>
          </MuiThemeProvider>
        </QueryParamProvider>
      </Router>
    </KeycloakProvider>
  )
}
