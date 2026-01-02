import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const BACKEND_HOST = 'backend'
const BACKEND_PORT = 8000

const BACKEND_HTTP_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`
const BACKEND_WS_URL = `ws://${BACKEND_HOST}:${BACKEND_PORT}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  base: '/gate-weimar-group-1/',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173, // Frontend port
    proxy: {
      '/api': {
        target: BACKEND_HTTP_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: BACKEND_WS_URL,
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
