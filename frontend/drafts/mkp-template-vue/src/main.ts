import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

// @ts-ignore
self.MonacoEnvironment = {
  // @ts-ignore
  getWorker(_, label) {
    return new editorWorker()
  },
}
const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')
