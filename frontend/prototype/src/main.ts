import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

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
const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
