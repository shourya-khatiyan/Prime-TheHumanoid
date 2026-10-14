import type { ComponentType } from 'react'
import { Alarms } from './Alarms'
import { Can } from './Can'
import { Commission } from './Commission'
import { Config } from './Config'
import { Console } from './Console'
import { Control } from './Control'
import { Dashboard } from './Dashboard'
import { Firmware } from './Firmware'
import { Health } from './Health'
import { Inspector } from './Inspector'
import { Recordings } from './Recordings'
import { Tests } from './Tests'

export type ViewDef = { id: string; label: string; key: string; component: ComponentType }

/** navigation order; `key` is the keyboard shortcut */
export const VIEWS: ViewDef[] = [
  { id: 'dashboard', label: 'dashboard', key: '1', component: Dashboard },
  { id: 'control', label: 'control', key: '2', component: Control },
  { id: 'commission', label: 'commissioning', key: '3', component: Commission },
  { id: 'health', label: 'health check', key: '4', component: Health },
  { id: 'tests', label: 'tests', key: '5', component: Tests },
  { id: 'config', label: 'configuration', key: '6', component: Config },
  { id: 'inspector', label: 'inspector', key: '7', component: Inspector },
  { id: 'console', label: 'console', key: '8', component: Console },
  { id: 'recordings', label: 'recordings', key: '9', component: Recordings },
  { id: 'can', label: 'can bus', key: '0', component: Can },
  { id: 'firmware', label: 'firmware', key: 'f', component: Firmware },
  { id: 'alarms', label: 'alarms / audit', key: 'a', component: Alarms },
]
