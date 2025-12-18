<template>
  <div class="test-area">
    <!-- Loading Overlay for Pyodide Initialization -->
    <div v-if="pyodideLoading" class="loading-overlay">
      <div class="loading-content">
        <div class="loading-spinner"></div>
        <h3>Initializing Python Runtime</h3>
        <p>Please wait while Pyodide loads...</p>
      </div>
    </div>

    <!-- Execution Loading Overlay -->
    <div v-if="isExecuting" class="execution-overlay">
      <div class="execution-content">
        <div class="loading-spinner"></div>
        <h3>Executing Code</h3>
        <p>Running transformation... ({{ executionTimeRemaining }}s remaining)</p>
        <button class="cancel-button" @click="cancelExecution">Cancel</button>
      </div>
    </div>

    <!-- Left Pane: Input, code editor, run, output -->
    <div class="left-panel">
      <!-- Input area -->
      <div class="input-section">
        <h3>Input Data:</h3>
        <textarea
          v-model="inputData"
          placeholder='{"channel_1":1, "channel_2":2}'
          :disabled="isExecuting"
        ></textarea>
      </div>

      <!-- Code editor + run button -->
      <div class="editor-pane">
        <div class="editor-header">
          <div class="editor-title">
            <span v-if="activeTransformId">
              Editing: <strong>{{ activeNodeName }}</strong>
            </span>
            <span v-else class="no-selection">No transform selected</span>
          </div>
          <button
            @click="handleSaveCode"
            :disabled="!editingCode || isExecuting"
            title="Save the current editor content into this transform node"
            class="save-code-button"
          >
            Save code
          </button>
        </div>

        <!-- Placeholder when no transform is selected -->
        <div v-if="!activeTransformId" class="editor-placeholder">
          <div class="placeholder-content">
            <div class="placeholder-icon">📝</div>
            <h3>No Transform Selected</h3>
            <p>
              Click a <strong>Transform</strong> node in the graph on the right to edit its code
              here.
            </p>
          </div>
        </div>

        <!-- Monaco Editor (shown when transform is selected) -->
        <MonacoEditor
          v-else
          ref="monacoEditorRef"
          class="monaco-editor"
          :value="transformationCode"
          @change="handleEditorChange"
          language="python"
          :theme="'vs-dark'"
          :options="monacoOptions"
          @mounted="onEditorMounted"
        />

        <div class="run-section">
          <button
            class="run-button"
            @click="handleRunTransformation"
            :disabled="!canRun || isExecuting"
            :title="runButtonTooltip"
          >
            <span v-if="isExecuting" class="button-spinner"></span>
            <span v-else>▶️</span>
            {{ isExecuting ? 'Running...' : 'Run Transformation' }}
          </button>
        </div>

        <!-- Output area -->
        <div v-if="runExecuted" class="output-section">
          <h3 class="output-title">Output</h3>
          <div class="results-pane">
            <div
              class="validation-message"
              :class="{ error: !!errorOutput, success: !errorOutput }"
            >
              <span v-if="!errorOutput">✅ Transformation code executed successfully.</span>
              <span v-else>❌ An error occurred during execution.</span>
            </div>
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
            <div class="table-wrapper">
              <table class="output-table">
                <thead>
                  <tr>
                    <th v-for="col in tableColumns" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ridx) in tableRows" :key="ridx">
                    <td v-for="col in tableColumns" :key="col">{{ formatCellValue(row[col]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Chart Output Section -->
          <div v-if="chartOutput" class="chart-output-section">
            <h3>{{ chartTitle }}</h3>
            <div class="chart-wrapper">
              <canvas ref="chartCanvas" width="400" height="280" style="display: block"></canvas>
            </div>
          </div>

          <div v-if="otherOutput" class="other-output-section">
            <h3>Output:</h3>
            <pre class="other-output">{{ otherOutput }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Pane: Vue Flow graph + sandbox controls -->
    <div class="center-panel">
      <!-- Sandbox header -->
      <div class="sandbox-header">
        <div class="sandbox-title">
          Test Area · <span>Sandbox</span>
          <span v-if="pyodideLoading" class="pyodide-status loading">⏳ Loading Python...</span>
          <span v-else-if="pyodideError" class="pyodide-status error">❌ Python Error</span>
          <span v-else class="pyodide-status ready">✅ Python Ready</span>
        </div>
        <div class="sandbox-actions">
          <button class="sandbox-toggle" @click="debugNodes">Debug</button>
          <button class="sandbox-toggle" @click="toggleSandboxBanner">
            {{ showSandboxBanner ? 'Hide info' : 'Show info' }}
          </button>
          <button class="sandbox-back" @click="handleRequestSaveAndBack" :disabled="isExecuting">
            Save &amp; Back to Pipeline
          </button>
        </div>
      </div>

      <div v-if="showSandboxBanner" class="sandbox-banner">
        ⚠️ This is a <strong>sandbox</strong>. Changes here do <strong>not</strong> affect the live
        execution pipeline.
      </div>

      <!-- Graph view -->
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :class="{ dark: true }"
        class="test-flow"
        :default-viewport="{ zoom: 1 }"
        :min-zoom="0.2"
        :max-zoom="4"
        :connection-mode="ConnectionMode.Strict"
        @node-click="handleNodeClick"
      >
        <template #node-custom-input="nodeProps">
          <CustomInputNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>
        <template #node-custom-output="nodeProps">
          <CustomOutputNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>
        <template #node-custom-transform="nodeProps">
          <CustomTransformNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>

        <Background pattern-color="#aaa" :gap="16" />
        <Controls position="top-left">
          <ControlButton title="Fit View" @click="handleFitView"> ⤢ </ControlButton>
        </Controls>
        <Panel position="top-right">
          <div class="panel-info">
            <p style="margin: 0; font-size: 12px">
              Click a <strong>Transform</strong> node to edit / run its code here.
            </p>
          </div>
        </Panel>
      </VueFlow>
    </div>

    <!-- Custom Modal: Save Confirmation -->
    <Teleport to="body">
      <div
        v-if="showSaveConfirm"
        class="testarea-modal-overlay"
        @click.self="closeSaveConfirmModal"
      >
        <div class="testarea-modal-dialog">
          <div class="testarea-modal-header">
            <h3>Save changes to HomeView?</h3>
            <button class="testarea-modal-close-button" @click="closeSaveConfirmModal">
              &times;
            </button>
          </div>
          <div class="testarea-modal-body">
            <p>
              Do you want to update the main pipeline on the HomeView with the current sandbox
              edits?
            </p>
          </div>
          <div class="testarea-modal-footer">
            <button class="testarea-btn-secondary" @click="handleDiscardAndGoBack">
              No, keep HomeView as is
            </button>
            <button class="testarea-btn-primary" @click="handleSaveAndGoBack">
              Yes, save &amp; go back
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Custom Modal: Reset Input Confirmation -->
    <Teleport to="body">
      <div
        v-if="showResetInputConfirm"
        class="testarea-modal-overlay"
        @click.self="closeResetInputModal"
      >
        <div class="testarea-modal-dialog">
          <div class="testarea-modal-header">
            <h3>Change Input Data?</h3>
            <button class="testarea-modal-close-button" @click="closeResetInputModal">
              &times;
            </button>
          </div>
          <div class="testarea-modal-body">
            <p>
              You're switching to a different transform node. Do you want to clear the current input
              data for the new transformation?
            </p>
          </div>
          <div class="testarea-modal-footer">
            <button class="testarea-btn-secondary" @click="handleKeepInput">
              No, keep current input
            </button>
            <button class="testarea-btn-primary" @click="handleClearInput">Yes, clear input</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Custom Modal: Alert -->
    <Teleport to="body">
      <div v-if="alertModal.show" class="testarea-modal-overlay" @click.self="closeAlertModal">
        <div class="testarea-modal-dialog testarea-alert-dialog" :class="alertModal.type">
          <div class="testarea-modal-header">
            <h3>{{ alertModal.title }}</h3>
            <button class="testarea-modal-close-button" @click="closeAlertModal">&times;</button>
          </div>
          <div class="testarea-modal-body">
            <p>{{ alertModal.message }}</p>
          </div>
          <div class="testarea-modal-footer">
            <button class="testarea-btn-primary" @click="closeAlertModal">OK</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import MonacoEditor from 'monaco-editor-vue3'
import {
  ConnectionMode,
  VueFlow,
  useVueFlow,
  Panel,
  type Node,
  type Edge,
  type NodeMouseEvent,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls, ControlButton } from '@vue-flow/controls'
import CustomInputNode from '@/components/CustomInputNode.vue'
import CustomTransformNode from '@/components/CustomTransformNode.vue'
import CustomOutputNode from '@/components/CustomOutputNode.vue'
import { Chart as ChartJS, type ChartConfiguration, type ChartType } from 'chart.js/auto'

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface PyodideInterface {
  globals: {
    set: (name: string, value: unknown) => void
    get: (name: string) => unknown
    delete: (name: string) => void
  }
  runPythonAsync: (code: string) => Promise<unknown>
}

interface PyProxy {
  toJs: (options?: {
    dict_converter?: (entries: Iterable<[string, unknown]>) => unknown
  }) => unknown
  destroy: () => void
}

interface EditorInstance {
  getModel: () => EditorModel | null
}

interface EditorModel {
  getLineLength: (lineNumber: number) => number
}

interface MonacoGlobal {
  editor: {
    setModelMarkers: (
      model: EditorModel,
      owner: string,
      markers: Array<{
        startLineNumber: number
        startColumn: number
        endLineNumber: number
        endColumn: number
        message: string
        severity: number
      }>,
    ) => void
  }
  MarkerSeverity: {
    Error: number
    Warning: number
    Info: number
  }
}

interface TransformNodeData {
  content: string
  code?: string
}

interface AlertModalState {
  show: boolean
  type: 'info' | 'warning' | 'error'
  title: string
  message: string
}

// ============================================================================
// CONSTANTS
// ============================================================================

const NODE_TYPES = {
  INPUT: 'custom-input',
  TRANSFORM: 'custom-transform',
  OUTPUT: 'custom-output',
} as const

const STORAGE_KEYS = {
  GRAPH: 'testarea_graph',
} as const

/**
 * IMPORTANT: This route name MUST match the route definition in router/index.ts
 * CustomTransformNode.vue checks: route.name === 'test-area'
 */
const ROUTE_NAMES = {
  HOME: 'home',
  TEST_AREA: 'test-area',
} as const

const PYODIDE_CONFIG = {
  INDEX_URL: 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/',
  EXECUTION_TIMEOUT_MS: 30000,
} as const

const EXAMPLE_JSON = '{"channel_1": 1, "channel_2": 2}'

// ============================================================================
// GLOBAL STATE (Module Level)
// ============================================================================

declare const loadPyodide: (opts: {
  indexURL: string
  stdout?: (text: string) => void
  stderr?: (text: string) => void
}) => Promise<PyodideInterface>

declare const monaco: MonacoGlobal | undefined

let pyodideInstance: PyodideInterface | null = null
let pyodideLoadPromise: Promise<PyodideInterface> | null = null

// ============================================================================
// COMPONENT DEFINITION
// ============================================================================

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
    const router = useRouter()
    const { fromObject, toObject, fitView, updateNodeData, getNode } = useVueFlow()

    // Graph state
    const nodes = ref<Node[]>([])
    const edges = ref<Edge[]>([])

    // Editor state
    const transformationCode = ref<string>('')
    const inputData = ref<string>('')
    const editingCode = ref<boolean>(false)
    const activeTransformId = ref<string | null>(null)
    const monacoEditorRef = ref<{ editor: EditorInstance } | null>(null)

    // UI state
    const showSandboxBanner = ref<boolean>(true)
    const showSaveConfirm = ref<boolean>(false)
    const showResetInputConfirm = ref<boolean>(false)
    const pendingNodeSwitch = ref<Node | null>(null)

    // Pyodide state
    const pyodideLoading = ref<boolean>(true)
    const pyodideError = ref<string | null>(null)

    // Execution state
    const isExecuting = ref<boolean>(false)
    const executionTimeRemaining = ref<number>(PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS / 1000)
    const executionAbortController = ref<AbortController | null>(null)

    // Output state
    const consoleOutput = ref<string>('')
    const errorOutput = ref<string>('')
    const tableOutput = ref<boolean>(false)
    const tableColumns = ref<string[]>([])
    const tableRows = ref<Record<string, unknown>[]>([])
    const otherOutput = ref<string>('')
    const runExecuted = ref<boolean>(false)

    // Chart output state
    const chartOutput = ref<boolean>(false)
    const chartTitle = ref<string>('Chart')
    const chartCanvas = ref<HTMLCanvasElement | null>(null)
    let chartInstance: ChartJS | null = null

    // Alert modal state
    const alertModal = ref<AlertModalState>({
      show: false,
      type: 'info',
      title: '',
      message: '',
    })

    let editorInstance: EditorInstance | null = null
    let countdownInterval: ReturnType<typeof setInterval> | null = null
    let saveDebounceTimeout: ReturnType<typeof setTimeout> | null = null

    // ==========================================================================
    // COMPUTED PROPERTIES
    // ==========================================================================

    const canRun = computed<boolean>(() => {
      return (
        !!activeTransformId.value &&
        transformationCode.value.trim().length > 0 &&
        !pyodideLoading.value &&
        !pyodideError.value
      )
    })

    const runButtonTooltip = computed<string>(() => {
      if (pyodideLoading.value) {
        return 'Python runtime is still loading...'
      }
      if (pyodideError.value) {
        return 'Python runtime failed to load'
      }
      if (!activeTransformId.value) {
        return 'Select a Transform node first'
      }
      if (transformationCode.value.trim().length === 0) {
        return 'Enter some code to run'
      }
      return 'Run the transformation code'
    })

    const activeNodeName = computed<string>(() => {
      if (!activeTransformId.value) return ''
      const node = nodes.value.find((n) => n.id === activeTransformId.value)
      if (node && node.data && typeof node.data === 'object' && 'content' in node.data) {
        return (node.data as TransformNodeData).content || 'Unnamed Transform'
      }
      return 'Unnamed Transform'
    })

    // ==========================================================================
    // MONACO EDITOR OPTIONS
    // ==========================================================================

    const monacoOptions = {
      fontSize: 14,
      automaticLayout: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      wordWrap: 'on' as const,
      lineNumbers: 'on' as const,
      folding: true,
      renderLineHighlight: 'line' as const,
      tabSize: 4,
      insertSpaces: true,
    }

    // ==========================================================================
    // UTILITY FUNCTIONS
    // ==========================================================================

    const showAlert = (
      title: string,
      message: string,
      type: 'info' | 'warning' | 'error' = 'info',
    ): void => {
      alertModal.value = {
        show: true,
        type,
        title,
        message,
      }
    }

    const closeAlertModal = (): void => {
      alertModal.value.show = false
    }

    const formatCellValue = (value: unknown): string => {
      if (value === null) return 'null'
      if (value === undefined) return 'undefined'
      if (typeof value === 'boolean') return value ? '✓ true' : '✗ false'
      if (typeof value === 'number') {
        if (Number.isInteger(value)) return String(value)
        return value.toFixed(4)
      }
      if (typeof value === 'object') {
        try {
          return JSON.stringify(value)
        } catch {
          return String(value)
        }
      }
      return String(value)
    }

    const isPyProxy = (obj: unknown): obj is PyProxy => {
      return (
        obj !== null &&
        typeof obj === 'object' &&
        'toJs' in obj &&
        typeof (obj as PyProxy).toJs === 'function'
      )
    }

    const deepConvertToJS = (obj: unknown): unknown => {
      if (obj === null || obj === undefined) return obj

      if (isPyProxy(obj)) {
        try {
          const converted = obj.toJs({ dict_converter: Object.fromEntries })
          obj.destroy()
          return deepConvertToJS(converted)
        } catch {
          return obj
        }
      }

      if (obj instanceof Map) {
        const plain: Record<string, unknown> = {}
        obj.forEach((value, key) => {
          plain[String(key)] = deepConvertToJS(value)
        })
        return plain
      }

      if (Array.isArray(obj)) {
        return obj.map((item) => deepConvertToJS(item))
      }

      if (typeof obj === 'object') {
        const plain: Record<string, unknown> = {}
        for (const [key, value] of Object.entries(obj)) {
          plain[key] = deepConvertToJS(value)
        }
        return plain
      }

      return obj
    }

    const clearEditorMarkers = (): void => {
      if (editorInstance && typeof monaco !== 'undefined') {
        const model = editorInstance.getModel()
        if (model) {
          monaco.editor.setModelMarkers(model, 'owner', [])
        }
      }
    }

    const setEditorErrorMarker = (lineNumber: number, message: string): void => {
      if (editorInstance && typeof monaco !== 'undefined') {
        const model = editorInstance.getModel()
        if (model && Number.isFinite(lineNumber) && lineNumber > 0) {
          const endColumn = model.getLineLength(lineNumber) + 1
          monaco.editor.setModelMarkers(model, 'owner', [
            {
              startLineNumber: lineNumber,
              startColumn: 1,
              endLineNumber: lineNumber,
              endColumn,
              message,
              severity: monaco.MarkerSeverity.Error,
            },
          ])
        }
      }
    }

    const extractLineNumberFromError = (errorMessage: string): number | null => {
      const match = errorMessage.match(/line\s+(\d+)/i)
      if (match && match[1]) {
        const lineNum = Number.parseInt(match[1], 10)
        const adjustedLine = lineNum - 35
        return adjustedLine > 0 ? adjustedLine : lineNum
      }
      return null
    }

    const debugNodes = (): void => {
      console.log('=== DEBUG INFO ===')
      console.log('nodes.value:', JSON.stringify(nodes.value, null, 2))
      console.log('activeTransformId:', activeTransformId.value)
      console.log('transformationCode:', transformationCode.value)

      const nodeInfo = nodes.value.map((n) => ({
        id: n.id,
        type: n.type,
        hasCode: !!(n.data as TransformNodeData)?.code,
        codeLength: ((n.data as TransformNodeData)?.code || '').length,
      }))
      showAlert('Debug Info', JSON.stringify(nodeInfo, null, 2), 'info')
    }

    /**
     * Syncs the current editor content back to the active node's data
     * This updates both the local nodes array AND Vue Flow's internal state
     * CustomTransformNode.vue will receive this via its watch on props.data.code
     */
    const syncEditorToNode = (): void => {
      if (!activeTransformId.value) return

      const nodeIndex = nodes.value.findIndex((n) => n.id === activeTransformId.value)

      if (nodeIndex === -1) {
        console.warn('Cannot sync - node not found:', activeTransformId.value)
        return
      }

      const currentNode = nodes.value[nodeIndex]
      if (!currentNode) return

      const currentData = (currentNode.data || {}) as TransformNodeData

      // Update our local nodes array
      nodes.value[nodeIndex] = {
        ...currentNode,
        data: {
          ...currentData,
          code: transformationCode.value,
        },
      }

      // Update Vue Flow's internal state - this triggers CustomTransformNode's watch
      updateNodeData(activeTransformId.value, {
        ...currentData,
        code: transformationCode.value,
      })

      console.log(
        'Synced code to node:',
        activeTransformId.value,
        'length:',
        transformationCode.value.length,
      )
    }

    /**
     * Destroys the current chart instance if it exists
     */
    const destroyChart = (): void => {
      if (chartInstance) {
        chartInstance.destroy()
        chartInstance = null
      }
    }

    const clearOutputs = (): void => {
      consoleOutput.value = ''
      errorOutput.value = ''
      otherOutput.value = ''
      tableOutput.value = false
      tableColumns.value = []
      tableRows.value = []
      // Clear chart output
      chartOutput.value = false
      chartTitle.value = 'Chart'
      destroyChart()
      runExecuted.value = false
      clearEditorMarkers()
    }

    const completeNodeSwitch = (clearInput: boolean): void => {
      if (!pendingNodeSwitch.value) return

      if (clearInput) {
        inputData.value = ''
      }

      clearOutputs()

      const nodeId = pendingNodeSwitch.value.id
      const targetNode = nodes.value.find((n) => n.id === nodeId)

      if (targetNode && targetNode.data) {
        const nodeData = targetNode.data as TransformNodeData
        activeTransformId.value = nodeId
        transformationCode.value = nodeData.code || ''
        editingCode.value = true
      }

      pendingNodeSwitch.value = null
      showResetInputConfirm.value = false
    }

    // ==========================================================================
    // EVENT HANDLERS
    // ==========================================================================

    /**
     * Handles node click events from Vue Flow
     * CustomTransformNode.vue checks isInTestArea and returns early from onModalToggle,
     * allowing this handler to manage the code editing in TestArea
     */
    const handleNodeClick = (event: NodeMouseEvent): void => {
      const clickedNodeId = event.node.id
      const clickedNodeType = event.node.type

      console.log('=== NODE CLICK ===')
      console.log('Clicked node ID:', clickedNodeId)
      console.log('Clicked node type:', clickedNodeType)

      if (clickedNodeType !== NODE_TYPES.TRANSFORM) {
        return
      }

      // If we're already editing this node, do nothing
      if (activeTransformId.value === clickedNodeId) {
        return
      }

      // Save current node's code before switching
      if (activeTransformId.value) {
        syncEditorToNode()
      }
      clearOutputs()

      const targetNode = nodes.value.find((n) => n.id === clickedNodeId)

      console.log('Target node from nodes.value:', targetNode)
      console.log('Target node data:', targetNode?.data)

      if (targetNode && targetNode.data) {
        const nodeData = targetNode.data as TransformNodeData
        activeTransformId.value = clickedNodeId
        transformationCode.value = nodeData.code || ''
        editingCode.value = true
        console.log('Loaded code, length:', transformationCode.value.length)
      } else {
        console.warn('No node found with id:', clickedNodeId)
        activeTransformId.value = clickedNodeId
        transformationCode.value = ''
        editingCode.value = true
      }
    }

    const handleEditorChange = (newValue: string): void => {
      transformationCode.value = newValue
    }

    const handleSaveCode = (): void => {
      if (!activeTransformId.value) {
        showAlert('No Transform Selected', 'Please select a transform node first.', 'warning')
        return
      }

      syncEditorToNode()

      const currentNode = getNode.value(activeTransformId.value)
      if (currentNode) {
        console.log('Code saved successfully:', {
          nodeId: activeTransformId.value,
          codePreview: transformationCode.value.substring(0, 50) + '...',
        })
      }

      showAlert('Code Saved', 'The code has been saved to the transform node.', 'info')
    }

    const handleFitView = (): void => {
      fitView()
    }

    const onEditorMounted = (editor: EditorInstance): void => {
      editorInstance = editor
    }

    const toggleSandboxBanner = (): void => {
      showSandboxBanner.value = !showSandboxBanner.value
    }

    // ==========================================================================
    // MODAL HANDLERS
    // ==========================================================================

    const closeResetInputModal = (): void => {
      showResetInputConfirm.value = false
      pendingNodeSwitch.value = null
    }

    const handleKeepInput = (): void => {
      completeNodeSwitch(false)
    }

    const handleClearInput = (): void => {
      completeNodeSwitch(true)
    }

    const handleRequestSaveAndBack = (): void => {
      syncEditorToNode()
      showSaveConfirm.value = true
    }

    const closeSaveConfirmModal = (): void => {
      showSaveConfirm.value = false
    }

    const handleSaveAndGoBack = (): void => {
      syncEditorToNode()
      const graph = toObject()
      sessionStorage.setItem(STORAGE_KEYS.GRAPH, JSON.stringify(graph))
      showSaveConfirm.value = false
      router.push({ name: ROUTE_NAMES.HOME })
    }

    const handleDiscardAndGoBack = (): void => {
      showSaveConfirm.value = false
      router.push({ name: ROUTE_NAMES.HOME })
    }

    // ==========================================================================
    // PYODIDE INITIALIZATION
    // ==========================================================================

    const initializePyodide = async (): Promise<PyodideInterface> => {
      if (pyodideInstance) {
        return pyodideInstance
      }

      if (pyodideLoadPromise) {
        return pyodideLoadPromise
      }

      pyodideLoadPromise = loadPyodide({
        indexURL: PYODIDE_CONFIG.INDEX_URL,
        stdout: (text: string) => {
          consoleOutput.value += text + '\n'
        },
        stderr: (text: string) => {
          if (text.includes('Error') || text.includes('Traceback')) {
            errorOutput.value += text + '\n'
          } else {
            consoleOutput.value += text + '\n'
          }
        },
      })

      pyodideInstance = await pyodideLoadPromise
      return pyodideInstance
    }

    // ==========================================================================
    // CODE EXECUTION
    // ==========================================================================

    const validateInputJson = (rawInput: string): Record<string, unknown> | null => {
      if (!rawInput) {
        showAlert(
          'No Input Data',
          `Please enter a JSON object in the Input Data field.\n\nExample: ${EXAMPLE_JSON}`,
          'warning',
        )
        errorOutput.value = `No input data. Example: ${EXAMPLE_JSON}`
        runExecuted.value = true
        return null
      }

      try {
        const parsed: unknown = JSON.parse(rawInput)

        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          showAlert(
            'Invalid Input Format',
            `Please provide a JSON object (not an array or primitive).\n\nExample: ${EXAMPLE_JSON}`,
            'warning',
          )
          errorOutput.value = `Input must be a JSON object. Example: ${EXAMPLE_JSON}`
          runExecuted.value = true
          return null
        }

        return parsed as Record<string, unknown>
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : String(e)
        showAlert(
          'Invalid JSON',
          `Failed to parse JSON input: ${message}\n\nExample: ${EXAMPLE_JSON}`,
          'error',
        )
        errorOutput.value = `Invalid JSON input: ${message}. Example: ${EXAMPLE_JSON}`
        runExecuted.value = true
        return null
      }
    }

    const buildPythonWrapper = (userCode: string): string => {
      const runId = Date.now()

      return `
import sys
import json
from io import StringIO

# ============================================================================
# COMPLETE STATE RESET - Clear ALL user-defined names from previous runs
# ============================================================================
_protected_names = {
    'sys', 'json', 'StringIO', '__builtins__', '__name__', '__doc__',
    '__js_input', '_run_id_${runId}', 'print', 'len', 'range', 'str',
    'int', 'float', 'list', 'dict', 'set', 'tuple', 'bool', 'type',
    'isinstance', 'hasattr', 'getattr', 'setattr', 'delattr', 'callable',
    'sum', 'min', 'max', 'abs', 'round', 'sorted', 'reversed', 'enumerate',
    'zip', 'map', 'filter', 'any', 'all', 'open', 'True', 'False', 'None'
}

_names_to_delete = [
    k for k in list(globals().keys())
    if k not in _protected_names and not k.startswith('__')
]
for _name in _names_to_delete:
    try:
        del globals()[_name]
    except:
        pass

# ============================================================================
# STDOUT/STDERR CAPTURE
# ============================================================================
_stdout_buffer = StringIO()
_stderr_buffer = StringIO()
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = _stdout_buffer
sys.stderr = _stderr_buffer

# ============================================================================
# LOGGER CLASS
# ============================================================================
class Logger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def warn(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")

logger = Logger()

# ============================================================================
# INPUT CONVERSION - Handle JS to Python conversion
# ============================================================================
def _convert_js_to_python(obj):
    if hasattr(obj, 'to_py'):
        result = obj.to_py()
        if isinstance(result, dict):
            return dict(result)
        return result
    return obj

_input_data = _convert_js_to_python(__js_input)
if isinstance(_input_data, dict):
    _input_data = dict(_input_data)

# ============================================================================
# TRACK FUNCTIONS BEFORE USER CODE
# ============================================================================
_functions_before = {k for k, v in globals().items() if callable(v)}

# ============================================================================
# USER CODE EXECUTION
# ============================================================================
${userCode}
# ============================================================================
# END USER CODE
# ============================================================================

# ============================================================================
# FIND AND EXECUTE USER FUNCTIONS
# ============================================================================
_functions_after = {
    k for k, v in globals().items()
    if callable(v) and not k.startswith('_') and k != 'Logger'
}
_user_functions = _functions_after - _functions_before

_result = None
_function_found = False
_tried_functions = []

# Priority order for function names
_priority_names = ['transform', 'main', 'process', 'run', 'execute', 'handle', 'compute']

# First, try priority function names
for _fname in _priority_names:
    if _fname in globals() and callable(globals()[_fname]):
        _tried_functions.append(_fname)
        try:
            _result = globals()[_fname](_input_data)
            _function_found = True
            break
        except Exception as e:
            print(f"Error calling {_fname}: {e}")

# If not found, try transform1, transform2, ... transform99
if not _function_found:
    for i in range(1, 100):
        _fname = f'transform{i}'
        if _fname in globals() and callable(globals()[_fname]):
            _tried_functions.append(_fname)
            try:
                _result = globals()[_fname](_input_data)
                _function_found = True
                break
            except Exception as e:
                print(f"Error calling {_fname}: {e}")

# If still not found, try ANY user-defined function
if not _function_found and _user_functions:
    for _fname in sorted(_user_functions):
        if _fname not in _tried_functions and _fname != 'logger':
            _tried_functions.append(_fname)
            try:
                _func = globals()[_fname]
                _result = _func(_input_data)
                _function_found = True
                print(f"Called function: {_fname}")
                break
            except Exception as e:
                print(f"Error calling {_fname}: {e}")

# ============================================================================
# RESTORE STDOUT/STDERR AND COLLECT OUTPUT
# ============================================================================
sys.stdout = _original_stdout
sys.stderr = _original_stderr

_captured_stdout = _stdout_buffer.getvalue()
_captured_stderr = _stderr_buffer.getvalue()

# ============================================================================
# RETURN RESULT DICTIONARY
# ============================================================================
{
    "result": _result,
    "stdout": _captured_stdout,
    "stderr": _captured_stderr,
    "function_found": _function_found,
    "tried_functions": _tried_functions,
    "user_functions": list(_user_functions)
}
`
    }

    /**
     * Renders a chart using Chart.js
     */
    const renderChart = async (chartData: Record<string, unknown>): Promise<void> => {
      console.log('=== RENDER CHART CALLED ===')
      console.log('Chart data:', chartData)

      destroyChart()

      const chartType = (chartData.chart_type as string) || 'bar'
      const title = (chartData.title as string) || 'Chart'
      const data = chartData.data as Record<string, unknown>[]

      console.log('Chart type:', chartType)
      console.log('Chart title:', title)
      console.log('Data points:', data?.length)

      if (!data || !Array.isArray(data)) {
        console.error('Invalid chart data - data is not an array')
        return
      }

      // Set chart output to true FIRST so the canvas renders
      chartTitle.value = title
      chartOutput.value = true
      console.log('chartOutput set to true')

      // Wait for DOM to update and canvas to be available
      await nextTick()
      console.log('After first nextTick')

      // Small additional delay to ensure canvas is mounted
      await new Promise((resolve) => setTimeout(resolve, 100))
      console.log('After delay, checking canvas...')

      if (!chartCanvas.value) {
        console.error('Chart canvas not found after waiting')
        console.log('chartOutput.value:', chartOutput.value)
        console.log('runExecuted.value:', runExecuted.value)
        return
      }

      console.log('Canvas found, getting context...')
      const ctx = chartCanvas.value.getContext('2d')
      if (!ctx) {
        console.error('Could not get canvas context')
        return
      }

      console.log('Context obtained, building chart config...')

      // Build chart configuration based on chart type
      let config: ChartConfiguration

      if (chartType === 'pie' || chartType === 'doughnut') {
        // Pie/Doughnut chart
        const labels = data.map((d) => String(d.name || d.label || d.category || ''))
        const values = data.map((d) => Number(d.value || d.count || 0))
        const colors = generateColors(data.length)

        config = {
          type: chartType as ChartType,
          data: {
            labels,
            datasets: [
              {
                data: values,
                backgroundColor: colors,
                borderColor: colors.map((c) => c.replace('0.7', '1')),
                borderWidth: 1,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'right', labels: { color: '#e2e8f0' } },
              title: { display: false },
            },
          },
        }
      } else if (chartType === 'scatter') {
        // Scatter plot
        const points = data.map((d) => ({
          x: Number(d.x || 0),
          y: Number(d.y || 0),
        }))

        config = {
          type: 'scatter',
          data: {
            datasets: [
              {
                label: (chartData.label as string) || 'Data Points',
                data: points,
                backgroundColor: 'rgba(59, 130, 246, 0.7)',
                borderColor: 'rgba(59, 130, 246, 1)',
                pointRadius: 5,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                title: {
                  display: true,
                  text: (chartData.x_label as string) || 'X',
                  color: '#94a3b8',
                },
                grid: { color: 'rgba(148, 163, 184, 0.2)' },
                ticks: { color: '#94a3b8' },
              },
              y: {
                title: {
                  display: true,
                  text: (chartData.y_label as string) || 'Y',
                  color: '#94a3b8',
                },
                grid: { color: 'rgba(148, 163, 184, 0.2)' },
                ticks: { color: '#94a3b8' },
              },
            },
            plugins: {
              legend: { labels: { color: '#e2e8f0' } },
            },
          },
        }
      } else {
        // Line, bar, area charts
        const firstDataPoint = data[0] ?? {}
        const xAxis: string = (chartData.x_axis as string) || Object.keys(firstDataPoint)[0] || 'x'
        const series: string[] =
          (chartData.series as string[]) || Object.keys(firstDataPoint).filter((k) => k !== xAxis)
        const labels = data.map((d) => String(d[xAxis] ?? ''))
        const colors = generateColors(series.length)

        const datasets = series.map((s, idx) => {
          const color = colors[idx] ?? 'rgba(59, 130, 246, 0.7)'
          return {
            label: s,
            data: data.map((d) => Number(d[s] || 0)),
            backgroundColor: chartType === 'line' ? 'transparent' : color,
            borderColor: color.replace('0.7', '1'),
            borderWidth: 2,
            fill: chartType === 'area',
            tension: 0.3,
          }
        })

        config = {
          type: (chartType === 'area' ? 'line' : chartType) as ChartType,
          data: { labels, datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                grid: { color: 'rgba(148, 163, 184, 0.2)' },
                ticks: { color: '#94a3b8' },
              },
              y: {
                grid: { color: 'rgba(148, 163, 184, 0.2)' },
                ticks: { color: '#94a3b8' },
              },
            },
            plugins: {
              legend: { labels: { color: '#e2e8f0' } },
            },
          },
        }
      }

      console.log('Creating chart with config type:', config.type)
      console.log('Config:', JSON.stringify(config, null, 2))

      try {
        chartInstance = new ChartJS(ctx, config)
        console.log('=== CHART CREATED SUCCESSFULLY ===')
      } catch (chartError) {
        console.error('=== CHART CREATION FAILED ===', chartError)
        // Reset state on failure
        chartOutput.value = false
        chartTitle.value = ''
        throw chartError // Re-throw to be caught by outer catch
      }
    }

    /**
     * Generates an array of colors for chart datasets
     */
    const generateColors = (count: number): string[] => {
      const baseColors: readonly string[] = [
        'rgba(59, 130, 246, 0.7)', // Blue
        'rgba(34, 197, 94, 0.7)', // Green
        'rgba(249, 115, 22, 0.7)', // Orange
        'rgba(168, 85, 247, 0.7)', // Purple
        'rgba(236, 72, 153, 0.7)', // Pink
        'rgba(20, 184, 166, 0.7)', // Teal
        'rgba(245, 158, 11, 0.7)', // Amber
        'rgba(239, 68, 68, 0.7)', // Red
        'rgba(99, 102, 241, 0.7)', // Indigo
        'rgba(16, 185, 129, 0.7)', // Emerald
      ] as const
      const colors: string[] = []
      for (let i = 0; i < count; i++) {
        const color = baseColors[i % baseColors.length]
        if (color) {
          colors.push(color)
        }
      }
      return colors
    }

    /**
     * Checks if the result is chart data
     */
    const isChartData = (result: unknown): result is Record<string, unknown> => {
      if (typeof result !== 'object' || result === null || Array.isArray(result)) {
        return false
      }
      const obj = result as Record<string, unknown>
      return 'chart_type' in obj && 'data' in obj && Array.isArray(obj.data)
    }

    /**
     * Checks if user explicitly requested a specific output type
     */
    const getExplicitOutputType = (result: unknown): string | null => {
      if (typeof result !== 'object' || result === null || Array.isArray(result)) {
        return null
      }
      const obj = result as Record<string, unknown>
      if ('output_type' in obj && typeof obj.output_type === 'string') {
        return obj.output_type.toLowerCase()
      }
      return null
    }

    /**
     * Extracts the actual data from a result object (removes metadata like output_type)
     */
    const extractResultData = (result: Record<string, unknown>): unknown => {
      if ('data' in result) {
        return result.data
      }
      // Remove output_type and return the rest
      const copy = { ...result }
      delete copy.output_type
      return copy
    }

    const processExecutionResult = (result: unknown): void => {
      if (result === null || result === undefined) {
        if (!consoleOutput.value) {
          consoleOutput.value = '(No output value, code executed successfully)'
        }
        return
      }

      if (typeof result === 'string') {
        otherOutput.value = result
        return
      }

      // Check for explicit output_type first
      const explicitType = getExplicitOutputType(result)

      if (explicitType === 'json') {
        // User explicitly requested JSON output
        const dataToShow =
          typeof result === 'object' && result !== null && !Array.isArray(result)
            ? extractResultData(result as Record<string, unknown>)
            : result
        try {
          otherOutput.value = JSON.stringify(dataToShow, null, 2)
        } catch {
          otherOutput.value = String(dataToShow)
        }
        return
      }

      if (explicitType === 'table') {
        // User explicitly requested table output
        const resultObj = result as Record<string, unknown>
        const tableData = resultObj.data as Record<string, unknown>[] | undefined

        if (tableData && Array.isArray(tableData) && tableData.length > 0) {
          const firstRow = tableData[0]
          if (typeof firstRow === 'object' && firstRow !== null) {
            tableColumns.value = Object.keys(firstRow as Record<string, unknown>)
            tableRows.value = tableData
            tableOutput.value = true
            return
          }
        }
        otherOutput.value = JSON.stringify(result, null, 2)
        return
      }

      if (explicitType === 'chart' || isChartData(result)) {
        // User explicitly requested chart OR auto-detected chart data
        renderChart(result as Record<string, unknown>).catch((err) => {
          console.error('Failed to render chart:', err)
          // Reset chart output since it failed
          chartOutput.value = false
          chartTitle.value = ''
          // Fall back to JSON display
          otherOutput.value = JSON.stringify(result, null, 2)
        })
        return
      }

      // Auto-detection for arrays (table vs JSON)
      if (Array.isArray(result)) {
        if (result.length === 0) {
          otherOutput.value = '[]'
          return
        }

        const firstItem = result[0]

        // Array of objects → Table
        if (typeof firstItem === 'object' && firstItem !== null && !Array.isArray(firstItem)) {
          const firstRow = firstItem as Record<string, unknown>
          tableColumns.value = Object.keys(firstRow)
          tableRows.value = result as Record<string, unknown>[]
          tableOutput.value = true
          return
        }

        // Array of arrays → Table
        if (Array.isArray(firstItem)) {
          tableColumns.value = (firstItem as unknown[]).map((_, idx) => `col${idx}`)
          tableRows.value = (result as unknown[][]).map((rowArr) => {
            const rowObj: Record<string, unknown> = {}
            rowArr.forEach((val, idx) => {
              rowObj[`col${idx}`] = val
            })
            return rowObj
          })
          tableOutput.value = true
          return
        }

        otherOutput.value = JSON.stringify(result, null, 2)
        return
      }

      // Objects without chart_type → JSON
      if (typeof result === 'object') {
        try {
          otherOutput.value = JSON.stringify(result, null, 2)
        } catch {
          otherOutput.value = String(result)
        }
        return
      }

      otherOutput.value = String(result)
    }

    const startCountdown = (): void => {
      executionTimeRemaining.value = PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS / 1000

      countdownInterval = setInterval(() => {
        executionTimeRemaining.value -= 1
        if (executionTimeRemaining.value <= 0) {
          stopCountdown()
        }
      }, 1000)
    }

    const stopCountdown = (): void => {
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
    }

    const cancelExecution = (): void => {
      if (executionAbortController.value) {
        executionAbortController.value.abort()
      }
      stopCountdown()
      isExecuting.value = false
      errorOutput.value = 'Execution cancelled by user.'
      runExecuted.value = true
    }

    const clearPyodideGlobals = (): void => {
      if (!pyodideInstance) return

      const globalsToDelete = [
        '__js_input',
        '_result',
        '_input_data',
        '_function_found',
        '_tried_functions',
        '_user_functions',
        '_functions_before',
        '_functions_after',
        'transform',
        'transform1',
        'transform2',
        'transform3',
        'transform4',
        'transform5',
        'transform6',
        'transform7',
        'transform8',
        'transform9',
        'transform10',
        'main',
        'run',
        'process',
        'execute',
        'handle',
        'compute',
        'row',
        'output',
        'result',
        'data',
        'input_data',
        'logger',
        'Logger',
        '_stdout_buffer',
        '_stderr_buffer',
        '_original_stdout',
        '_original_stderr',
        '_captured_stdout',
        '_captured_stderr',
        '_convert_js_to_python',
        '_protected_names',
        '_names_to_delete',
        '_priority_names',
        '_fname',
        '_func',
      ]

      for (const name of globalsToDelete) {
        try {
          pyodideInstance.globals.delete(name)
        } catch {}
      }
    }

    const handleRunTransformation = async (): Promise<void> => {
      if (!pyodideInstance) {
        showAlert(
          'Python Not Ready',
          'The Python runtime is still loading. Please wait a moment and try again.',
          'warning',
        )
        return
      }

      if (!activeTransformId.value) {
        showAlert(
          'No Transform Selected',
          'Please click on a Transform node in the graph to select it before running.',
          'warning',
        )
        return
      }

      // Sync current code to node
      syncEditorToNode()

      // Clear ALL output state before each run
      consoleOutput.value = ''
      errorOutput.value = ''
      otherOutput.value = ''
      tableOutput.value = false
      tableColumns.value = []
      tableRows.value = []
      runExecuted.value = false
      clearEditorMarkers()

      // Validate input
      const rawInput = inputData.value.trim()
      const inputObj = validateInputJson(rawInput)
      if (!inputObj) {
        return
      }

      isExecuting.value = true
      executionAbortController.value = new AbortController()
      startCountdown()

      try {
        // Clear Pyodide globals before execution
        clearPyodideGlobals()

        // Set input in Pyodide globals
        pyodideInstance.globals.set('__js_input', inputObj)

        const userCode = transformationCode.value
        console.log('==== CODE BEING EXECUTED ====')
        console.log(userCode)
        console.log('==== INPUT DATA ====')
        console.log(inputObj)
        console.log('=============================')

        const wrappedCode = buildPythonWrapper(userCode)

        // Execute with timeout
        const timeoutPromise = new Promise<never>((_, reject) => {
          const timeoutId = setTimeout(() => {
            reject(
              new Error(
                `Execution timed out after ${PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS / 1000} seconds. Your code may contain an infinite loop.`,
              ),
            )
          }, PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS)

          executionAbortController.value?.signal.addEventListener('abort', () => {
            clearTimeout(timeoutId)
            reject(new Error('Execution cancelled'))
          })
        })

        const rawResult: unknown = await Promise.race([
          pyodideInstance.runPythonAsync(wrappedCode),
          timeoutPromise,
        ])

        runExecuted.value = true

        // Deep convert PyProxy/Map objects to plain JS
        const result = deepConvertToJS(rawResult) as {
          result?: unknown
          stdout?: string
          stderr?: string
          function_found?: boolean
          tried_functions?: string[]
          user_functions?: string[]
        } | null

        console.log('==== EXECUTION RESULT ====')
        console.log(result)
        console.log('==========================')

        // Process the result
        if (result && typeof result === 'object') {
          // Add captured stdout to console output
          if (result.stdout) {
            consoleOutput.value += result.stdout
          }

          // Add captured stderr to error output (if any)
          if (result.stderr && result.stderr.trim()) {
            errorOutput.value += result.stderr
          }

          // Log debug info
          if (result.tried_functions) {
            console.log('Tried functions:', result.tried_functions)
          }
          if (result.user_functions) {
            console.log('User functions found:', result.user_functions)
          }

          // Check if a function was found
          if (!result.function_found) {
            consoleOutput.value +=
              '\n⚠️ No transform function found. Define a function like:\n' +
              'def transform(row: dict) -> dict:\n' +
              '    # your code here\n' +
              '    return row\n'
          }

          // Process the actual result
          const actualResult = deepConvertToJS(result.result)
          processExecutionResult(actualResult)
        } else {
          processExecutionResult(result)
        }

        // Ensure we show something if nothing else was output
        if (
          !consoleOutput.value &&
          !otherOutput.value &&
          !tableOutput.value &&
          !chartOutput.value &&
          !errorOutput.value
        ) {
          consoleOutput.value = '(Code executed successfully with no output)'
        }

        clearEditorMarkers()
      } catch (err: unknown) {
        runExecuted.value = true

        const errMsg = err instanceof Error ? err.message : String(err)
        errorOutput.value = errMsg

        console.error('Execution error:', errMsg)

        // Try to set error marker in editor
        const lineNumber = extractLineNumberFromError(errMsg)
        if (lineNumber !== null) {
          setEditorErrorMarker(lineNumber, errMsg)
        }
      } finally {
        stopCountdown()
        isExecuting.value = false
        executionAbortController.value = null

        // Clean up Pyodide globals
        try {
          pyodideInstance?.globals.delete('__js_input')
        } catch {
          // Ignore cleanup errors
        }
      }
    }

    // ==========================================================================
    // LIFECYCLE HOOKS
    // ==========================================================================

    onMounted(async () => {
      const storedGraph = sessionStorage.getItem(STORAGE_KEYS.GRAPH)
      if (storedGraph) {
        try {
          const graph = JSON.parse(storedGraph)

          console.log('Loading graph from sessionStorage:', graph)

          if (graph.nodes && Array.isArray(graph.nodes)) {
            nodes.value = graph.nodes as Node[]
            console.log(
              'Loaded nodes:',
              nodes.value.map((n) => ({
                id: n.id,
                type: n.type,
                hasCode: !!(n.data as TransformNodeData)?.code,
                codePreview: (n.data as TransformNodeData)?.code?.substring(0, 30),
              })),
            )
          }
          if (graph.edges && Array.isArray(graph.edges)) {
            edges.value = graph.edges as Edge[]
          }

          fromObject(graph)

          await nextTick()

          console.log('Graph loaded successfully')
        } catch (e) {
          console.error('Error parsing stored graph for TestArea:', e)
        }
      } else {
        console.warn('No graph found in sessionStorage')
      }

      try {
        await initializePyodide()
        pyodideLoading.value = false
        pyodideError.value = null
        console.log('Pyodide initialized successfully')
      } catch (err) {
        console.error('Failed to load Pyodide:', err)
        pyodideLoading.value = false
        pyodideError.value = err instanceof Error ? err.message : String(err)
      }
    })

    onUnmounted(() => {
      stopCountdown()

      if (executionAbortController.value) {
        executionAbortController.value.abort()
      }

      clearEditorMarkers()

      // Destroy chart instance
      destroyChart()

      if (saveDebounceTimeout) {
        clearTimeout(saveDebounceTimeout)
      }
    })

    // ==========================================================================
    // WATCHERS
    // ==========================================================================

    watch(transformationCode, () => {
      if (saveDebounceTimeout) {
        clearTimeout(saveDebounceTimeout)
      }

      saveDebounceTimeout = setTimeout(() => {
        if (activeTransformId.value) {
          syncEditorToNode()
        }
      }, 1000)
    })

    // ==========================================================================
    // RETURN
    // ==========================================================================

    return {
      // Graph state
      nodes,
      edges,
      ConnectionMode,
      transformationCode,
      inputData,
      editingCode,
      activeTransformId,
      monacoEditorRef,
      monacoOptions,
      showSandboxBanner,
      showSaveConfirm,
      showResetInputConfirm,
      debugNodes,
      pyodideLoading,
      pyodideError,
      isExecuting,
      executionTimeRemaining,
      consoleOutput,
      errorOutput,
      tableOutput,
      tableColumns,
      tableRows,
      otherOutput,
      runExecuted,
      chartOutput,
      chartTitle,
      chartCanvas,
      alertModal,
      canRun,
      runButtonTooltip,
      activeNodeName,
      handleNodeClick,
      handleSaveCode,
      handleFitView,
      onEditorMounted,
      toggleSandboxBanner,
      handleRunTransformation,
      cancelExecution,
      closeAlertModal,
      closeResetInputModal,
      handleKeepInput,
      handleClearInput,
      handleEditorChange,
      handleRequestSaveAndBack,
      closeSaveConfirmModal,
      handleSaveAndGoBack,
      handleDiscardAndGoBack,
      formatCellValue,
    }
  },
})
</script>

<styles>
  STYLES MOVED TO MAIN STYLESHEET
</styles>
