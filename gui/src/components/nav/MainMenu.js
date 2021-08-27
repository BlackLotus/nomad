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
import { MenuBar, MenuBarItem, MenuBarMenu } from './MenuBar'
import { useCookies } from 'react-cookie'
import Consent from './Consent'
import { routes } from './Routes'

const MainMenu = React.memo(function MainMenu() {
  const cookies = useCookies()[0]
  const [consentOpen, setConsentOpen] = useState(cookies['terms-accepted'] !== 'true')

  const handleConsentAccept = useCallback(() => {
    setConsentOpen(false)
  }, [])

  return <MenuBar>
    {routes.filter(route => route.menu).map((menuRoute, i) => (
      <MenuBarMenu key={i} label={menuRoute.menu} route={'/' + menuRoute.path}>
        {menuRoute.routes.filter(route => route.menu).map((itemRoute, i) => (
          <MenuBarItem
            key={i} label={itemRoute.menu} tooltip={itemRoute.tooltip}
            route={itemRoute.path && `/${menuRoute.path}/${itemRoute.path}`}
            href={itemRoute.href} onClick={itemRoute.consent && (() => setConsentOpen(true))}
          />
        ))}
      </MenuBarMenu>
    ))}
    <Consent open={consentOpen} onAccept={handleConsentAccept}/>
  </MenuBar>
})

export default MainMenu
