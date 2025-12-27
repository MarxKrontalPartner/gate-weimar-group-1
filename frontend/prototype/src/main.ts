import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

import UIkit from 'uikit'
import Icons from 'uikit/dist/js/uikit-icons'

import { createI18n } from 'vue-i18n'
import { TranslationsEN } from './assets/translations.en'
import { TranslationsDE } from './assets/translations.de'

declare global {
  interface Window {
    MonacoEnvironment: {
      getWorker(moduleId: string, label: string): Worker
    }
  }
}

self.MonacoEnvironment = {
  getWorker(): Worker {
    return new editorWorker()
  },
}

UIkit.use(Icons)

const app = createApp(App)

const i18n = createI18n({
  locale: 'de',
  fallbackLocale: 'en',
  legacy: false,
  messages: {
    en: TranslationsEN,
    de: TranslationsDE,
  },
})

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')
