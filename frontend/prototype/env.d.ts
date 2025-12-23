/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>
  export default component
}

declare module 'monaco-editor-vue3' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export const MonacoEditor: DefineComponent<any, any, any>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export const CodeEditor: DefineComponent<any, any, any>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const defaultExport: DefineComponent<any, any, any>
  export default defaultExport
}
