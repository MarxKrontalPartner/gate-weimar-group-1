<template>
  <div class="test-area">
    <!-- Left Pane: code editor + run -->
    <div class="left-panel">
      <div class="editor-pane">
        <div class="editor-header">
          <div>
            <label>Language:</label>
            <select v-model="transformLanguage">
              <option value="python">Python</option>
              <option value="sql">SQL</option>
            </select>
          </div>
          <button @click="closeEditor" :disabled="!editingCode">
            ✓ Done
          </button>
        </div>

        <MonacoEditor
          class="monaco-editor"
          v-model="transformationCode"
          :language="transformLanguage"
          :theme="'vs-dark'"
          :options="monacoOptions"
          @mounted="onEditorMounted"
        />

        <div class="run-section">
          <button class="run-button" @click="runTransformation" :disabled="!canRun">
            ▶️ Run Transformation
          </button>
        </div>
      </div>
    </div>

    <!-- Right Pane: Vue Flow graph + results -->
    <div class="center-panel">
      <!-- Sandbox header + toggle + back -->
      <div class="sandbox-header">
        <div class="sandbox-title">
          Test Area · <span>Sandbox</span>
        </div>

        <div class="sandbox-actions">
          <button class="sandbox-toggle" @click="toggleSandboxBanner">
            {{ showSandboxBanner ? 'Hide info' : 'Show info' }}
          </button>
          <button class="sandbox-back" @click="requestSaveAndBack">
            Save &amp; Back to Pipeline
          </button>
        </div>
      </div>

      <!-- Banner itself -->
      <div v-if="showSandboxBanner" class="sandbox-banner">
        ⚠️ This is a <strong>sandbox</strong>. Changes here do <strong>not</strong> affect the live
        execution pipeline.
      </div>

      <VueFlow
        v-model="nodes"
        :edges="edges"
        :class="{ dark: true }"
        class="test-flow"
        :default-viewport="{ zoom: 1 }"
        :min-zoom="0.2"
        :max-zoom="4"
        :connection-mode="ConnectionMode.Strict"
      >
        <template #node-custom-input="props">
          <CustomInputNode :id="props.id" :data="props.data" />
        </template>

        <template #node-custom-output="props">
          <CustomOutputNode :id="props.id" :data="props.data" />
        </template>

        <template #node-custom-transform="props">
          <CustomTransformNode :id="props.id" :data="props.data" />
        </template>

        <Background pattern-color="#aaa" :gap="16" />

        <Controls position="top-left">
          <ControlButton title="Fit View" @click="fitView">
            ⤢
          </ControlButton>
        </Controls>

        <!-- Small info panel -->
        <Panel position="top-right">
          <div class="panel-info">
            <p style="margin: 0; font-size: 12px">
              Click a <strong>Transform</strong> node to edit / run its code here.
            </p>
          </div>
        </Panel>
      </VueFlow>

      <!-- Results pane (shows after run) -->
      <div v-if="runExecuted" class="results-pane">
        <div class="validation-message" :class="{ error: !!errorOutput }">
          <span v-if="!errorOutput">✅ Transformation code executed successfully.</span>
          <span v-else>❌ An error occurred during execution.</span>
        </div>

        <div v-if="consoleOutput" class="console-output-section">
          <h3>Console Output:</h3>
          <pre class="console-output">{{ consoleOutput }}</pre>
        </div>

        <div v-if="errorOutput" class="error-output-section">
          <h3>Error Details:</h3>
          <pre class="error-output">{{ errorOutput }}</pre>
        </div>

        <div v-if="tableOutput" class="table-output-section">
          <h3>Output Table:</h3>
          <table class="output-table">
            <thead>
              <tr>
                <th v-for="col in tableColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ridx) in tableRows" :key="ridx">
                <td v-for="col in tableColumns" :key="col">{{ row[col] }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="otherOutput" class="other-output-section">
          <h3>Output:</h3>
          <pre class="other-output">{{ otherOutput }}</pre>
        </div>
      </div>
    </div>

    <!-- Save confirmation dialog -->
    <div v-if="showSaveConfirm" class="save-confirm-overlay">
      <div class="save-confirm-dialog">
        <h3>Save changes to HomeView?</h3>
        <p>
          Do you want to update the main pipeline on the HomeView with the current sandbox edits?
        </p>
        <div class="save-confirm-actions">
          <button class="btn-yes" @click="saveAndGoBack">
            Yes, save &amp; go back
          </button>
          <button class="btn-no" @click="discardAndGoBack">
            No, keep HomeView as is
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
/* eslint-disable @typescript-eslint/no-explicit-any */

import { defineComponent, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import MonacoEditor from 'monaco-editor-vue3'

import {
  ConnectionMode,
  VueFlow,
  useVueFlow,
  Panel,
  type Node,
  type Edge,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls, ControlButton } from '@vue-flow/controls'

import CustomInputNode from '@/components/CustomInputNode.vue'
import CustomTransformNode from '@/components/CustomTransformNode.vue'
import CustomOutputNode from '@/components/CustomOutputNode.vue'

// globals from CDN / bundler
declare const loadPyodide: (opts: unknown) => Promise<any>
declare const monaco: any

let pyodide: any = null

export default defineComponent({
  name: 'TestArea',
  components: {
    MonacoEditor,
    VueFlow,
    Background,
    Controls,
    ControlButton,
    Panel,
    CustomInputNode,
    CustomTransformNode,
    CustomOutputNode,
  },
  setup() {
    const nodes = ref<Node[]>([])
    const edges = ref<Edge[]>([])
    const router = useRouter()

    const { fromObject, toObject, onNodeClick, fitView, updateNodeData } = useVueFlow()

    const transformationCode = ref<string>('')
    const transformLanguage = ref<'python' | 'sql'>('python')
    const editingCode = ref<boolean>(false)
    const activeTransformId = ref<string | null>(null)

    const showSandboxBanner = ref<boolean>(true)
    const toggleSandboxBanner = () => {
      showSandboxBanner.value = !showSandboxBanner.value
    }

    const showSaveConfirm = ref<boolean>(false)

    // write current editor contents back into the active node (Vue Flow internal state)
    const syncEditorToNode = () => {
      if (!activeTransformId.value) return
      updateNodeData(activeTransformId.value, {
        code: transformationCode.value,
      })
    }

    // When user clicks a transform node, first persist previous node, then load the new one
    onNodeClick(({ node }: any) => {
      if (node.type === 'custom-transform') {
        // store previous transform’s code
        syncEditorToNode()

        activeTransformId.value = node.id
        // read code from the current graph (nodes ref mirrors Vue Flow after fromObject)
        const n = nodes.value.find((nd) => nd.id === node.id) as any
        transformationCode.value = n?.data?.code ?? ''
        editingCode.value = true
      }
    })

    const consoleOutput = ref<string>('')
    const errorOutput = ref<string>('')
    const tableOutput = ref<boolean>(false)
    const tableColumns = ref<string[]>([])
    const tableRows = ref<Record<string, unknown>[]>([])
    const otherOutput = ref<string>('')
    const runExecuted = ref<boolean>(false)

    const monacoOptions = {
      fontSize: 14,
      automaticLayout: true,
    }

    const canRun = ref<boolean>(false)
    const updateCanRun = () => {
      canRun.value = !!activeTransformId.value && transformationCode.value.trim().length > 0
    }

    watch([transformationCode, activeTransformId], updateCanRun, {
      immediate: true,
    })

    let editorInstance: any = null
    const onEditorMounted = (editor: any) => {
      editorInstance = editor
    }

    const closeEditor = () => {
      syncEditorToNode()
      editingCode.value = false
    }

    // open confirm dialog: we already sync code from editor to node
    const requestSaveAndBack = () => {
      syncEditorToNode()
      showSaveConfirm.value = true
    }

    // YES → persist sandbox graph to HomeView and leave
    const saveAndGoBack = () => {
      syncEditorToNode()
      const graph = toObject()
      sessionStorage.setItem('testarea_graph', JSON.stringify(graph))
      showSaveConfirm.value = false
      router.push({ name: 'home' })
    }

    // NO → do not change sessionStorage; just go back
    const discardAndGoBack = () => {
      showSaveConfirm.value = false
      router.push({ name: 'home' })
    }

    // Load graph from HomeView + Pyodide
    onMounted(async () => {
      const storedGraph = sessionStorage.getItem('testarea_graph')
      if (storedGraph) {
        try {
          const graph = JSON.parse(storedGraph)
          fromObject(graph)
          const obj = toObject()
          nodes.value = obj.nodes as Node[]
          edges.value = obj.edges as Edge[]
        } catch (e) {
          console.error('Error parsing stored graph for TestArea:', e)
        }
      }

      // load pyodide
      try {
        const py = await loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/',
          stdout: (text: string) => {
            consoleOutput.value += text + '\n'
          },
          stderr: (text: string) => {
            errorOutput.value += text + '\n'
          },
        })
        pyodide = py
      } catch (err: any) {
        console.error('Failed to load Pyodide:', err)
      }
    })

    const runTransformation = async () => {
      if (!pyodide) {
        alert('Python runtime is still loading. Please wait.')
        return
      }
      if (!activeTransformId.value) {
        alert('Please click a Transform node to select which code to run.')
        return
      }

      consoleOutput.value = ''
      errorOutput.value = ''
      otherOutput.value = ''
      tableOutput.value = false
      tableColumns.value = []
      tableRows.value = []
      runExecuted.value = false

      const codeToRun = transformationCode.value

      try {
        let result: any
        if (transformLanguage.value === 'python') {
          result = await pyodide.runPythonAsync(codeToRun)
        } else {
          pyodide.globals.set('SQL_QUERY', codeToRun)
          const sqlChecker = `
import sqlite3
conn = sqlite3.connect(':memory:')
cur = conn.cursor()
try:
    cur.execute('EXPLAIN QUERY PLAN ' + SQL_QUERY)
finally:
    conn.close()
'SQL OK'
`
          result = await pyodide.runPythonAsync(sqlChecker)
        }

        runExecuted.value = true

        if (result !== undefined && result !== null) {
          if ((result as any).toJs) {
            try {
              result = (result as any).toJs()
            } catch {
              // ignore conversion failure
            }
          }
          if (typeof result === 'string') {
            otherOutput.value = result
          } else if (Array.isArray(result)) {
            if (
              result.length > 0 &&
              typeof result[0] === 'object' &&
              !Array.isArray(result[0])
            ) {
              const first = result[0] as Record<string, unknown>
              tableColumns.value = Object.keys(first)
              tableRows.value = result as Record<string, unknown>[]
              tableOutput.value = true
            } else if (result.length > 0 && Array.isArray(result[0])) {
              const firstRow = result[0] as any[]
              tableColumns.value = firstRow.map((_: any, idx: number) => 'col' + idx)
              tableRows.value = (result as any[]).map((rowArr: any[]) => {
                const rowObj: Record<string, unknown> = {}
                rowArr.forEach((val: unknown, idx: number) => {
                  rowObj['col' + idx] = val
                })
                return rowObj
              })
              tableOutput.value = true
            } else {
              otherOutput.value = JSON.stringify(result)
            }
          } else if (typeof result === 'object') {
            try {
              otherOutput.value = JSON.stringify(result, null, 2)
            } catch {
              otherOutput.value = String(result)
            }
          } else if (
            typeof result === 'number' ||
            typeof result === 'boolean'
          ) {
            otherOutput.value = String(result)
          }
        }

        if (!consoleOutput.value && !otherOutput.value && !tableOutput.value) {
          consoleOutput.value = '(No output, code executed successfully)'
        }

        if (editorInstance && typeof monaco !== 'undefined') {
          const model = editorInstance.getModel()
          if (model) {
            monaco.editor.setModelMarkers(model, 'owner', [])
          }
        }
      } catch (err: any) {
        runExecuted.value = true
        errorOutput.value = String(err)

        if (editorInstance && errorOutput.value && typeof monaco !== 'undefined') {
          const match = errorOutput.value.match(/line (\d+)/)
          if (match) {
            const lineNum = parseInt(match[1] as string, 10)
            const model = editorInstance.getModel()
            if (model) {
              monaco.editor.setModelMarkers(model, 'owner', [
                {
                  startLineNumber: lineNum,
                  startColumn: 1,
                  endLineNumber: lineNum,
                  endColumn: model.getLineLength(lineNum) + 1,
                  message: errorOutput.value,
                  severity: monaco.MarkerSeverity.Error,
                },
              ])
            }
          }
        }
      }
    }

    return {
      nodes,
      edges,
      ConnectionMode,
      fitView,
      transformationCode,
      transformLanguage,
      editingCode,
      monacoOptions,
      canRun,
      consoleOutput,
      errorOutput,
      tableOutput,
      tableColumns,
      tableRows,
      otherOutput,
      runExecuted,
      onEditorMounted,
      closeEditor,
      showSandboxBanner,
      toggleSandboxBanner,
      runTransformation,
      showSaveConfirm,
      requestSaveAndBack,
      saveAndGoBack,
      discardAndGoBack,
    }
  },
})
</script>

<style scoped>
/* same styles you already had, including sandbox banner + dialog */
.test-area {
  display: flex;
  height: 100vh;
  color: #f0f0f0;
  background: #1e1e1e;
}

.left-panel {
  width: 30%;
  background: #252526;
  padding: 0.5rem;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.editor-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e1e1e;
  padding: 0.5rem;
}

.editor-header select {
  background: #3c3c3c;
  color: #fff;
  border: 1px solid #555;
  padding: 0.2rem 0.5rem;
}

.editor-header button {
  background: #007acc;
  color: #fff;
  border: none;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
}

.monaco-editor {
  flex: 1;
  border: 1px solid #3c3c3c;
}

.center-panel {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.sandbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  padding: 6px 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, #0f172a, #1d4ed8, #06b6d4);
  box-shadow: 0 0 12px rgba(37, 99, 235, 0.45);
}

.sandbox-title {
  font-size: 14px;
  font-weight: 600;
  color: #e5f2ff;
}

.sandbox-title span {
  color: #a5f3fc;
}

.sandbox-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sandbox-toggle {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(226, 232, 240, 0.7);
  background: rgba(15, 23, 42, 0.6);
  color: #e2e8f0;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.1s ease;
}

.sandbox-toggle:hover {
  background: rgba(15, 23, 42, 0.9);
  transform: translateY(-1px);
}

.sandbox-back {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  color: #e5fdf5;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
}

.sandbox-back:hover {
  background: linear-gradient(90deg, #4ade80, #22c55e);
}

.sandbox-banner {
  background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.25), rgba(15, 23, 42, 0.95));
  border: 1px solid rgba(59, 130, 246, 0.7);
  color: #e0f2fe;
  padding: 8px 12px;
  margin-bottom: 10px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}

.test-flow {
  flex: 1;
  border: 1px solid #444;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.panel-info {
  background: rgba(0, 0, 0, 0.5);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.run-section {
  margin-top: 0.5rem;
}

.run-button {
  background: #28a745;
  color: #fff;
  border: none;
  padding: 0.6rem 1.2rem;
  font-size: 0.95rem;
  cursor: pointer;
  border-radius: 4px;
}

.run-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.results-pane {
  margin-top: 0.5rem;
  background: #202020;
  padding: 1rem;
  border-radius: 4px;
}

.validation-message {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.validation-message.error {
  color: #ff6060;
}

.console-output-section,
.error-output-section,
.table-output-section,
.other-output-section {
  margin-top: 0.5rem;
}

.console-output,
.error-output,
.other-output {
  background: #000;
  color: #0f0;
  padding: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.error-output {
  color: #ff8080;
}

.output-table {
  width: 100%;
  border-collapse: collapse;
}

.output-table th,
.output-table td {
  border: 1px solid #555;
  padding: 0.3rem 0.5rem;
}

/* Save confirmation dialog */
.save-confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.save-confirm-dialog {
  width: 420px;
  max-width: 90vw;
  background: radial-gradient(circle at top left, #1e293b, #020617);
  border-radius: 12px;
  padding: 18px 20px 16px;
  box-shadow: 0 0 25px rgba(37, 99, 235, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.8);
  color: #e5f0ff;
  text-align: center;
}

.save-confirm-dialog h3 {
  margin: 0 0 8px;
  font-size: 18px;
}

.save-confirm-dialog p {
  margin: 0 0 16px;
  font-size: 13px;
  color: #cbd5f5;
}

.save-confirm-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.save-confirm-actions .btn-yes,
.save-confirm-actions .btn-no {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.save-confirm-actions .btn-yes {
  background: linear-gradient(90deg, #22c55e, #16a34a);
  color: #e5fdf5;
}

.save-confirm-actions .btn-no {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.7);
}
</style>
