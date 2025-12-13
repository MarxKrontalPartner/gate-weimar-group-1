import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

// Import UIKit JS + Icons
import UIkit from 'uikit'
import Icons from 'uikit/dist/js/uikit-icons'

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

app.use(createPinia())
app.use(router)

app.mount('#app')
