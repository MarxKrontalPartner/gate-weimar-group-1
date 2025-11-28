import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import { MKPThemes } from '../themes.ts'

const isLightModePreferred = window.matchMedia('(prefers-color-scheme: light)').matches

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: isLightModePreferred ? 'mkpDarkTheme' : 'mkpLightTheme',
    themes: {
      mkpLightTheme: MKPThemes.mkpLightTheme,
      mkpDarkTheme: MKPThemes.mkpDarkTheme,
    },
  },
  defaults: {
    VAppBar: {
      VIcon: {
        color: 'on-surface',
      },
    },
  },
})
