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
      <div v-if="showSaveConfirm" class="modal-overlay" @click.self="closeSaveConfirmModal">
        <div class="modal-dialog save-confirm-dialog">
          <div class="modal-header">
            <h3>Save changes to HomeView?</h3>
            <button class="modal-close-button" @click="closeSaveConfirmModal">&times;</button>
          </div>
          <div class="modal-body">
            <p>
              Do you want to update the main pipeline on the HomeView with the current sandbox
              edits?
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="handleDiscardAndGoBack">
              No, keep HomeView as is
            </button>
            <button class="btn-primary" @click="handleSaveAndGoBack">
              Yes, save &amp; go back
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Custom Modal: Reset Input Confirmation -->
    <Teleport to="body">
      <div v-if="showResetInputConfirm" class="modal-overlay" @click.self="closeResetInputModal">
        <div class="modal-dialog reset-input-dialog">
          <div class="modal-header">
            <h3>Change Input Data?</h3>
            <button class="modal-close-button" @click="closeResetInputModal">&times;</button>
          </div>
          <div class="modal-body">
            <p>
              You're switching to a different transform node. Do you want to clear the current input
              data for the new transformation?
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="handleKeepInput">No, keep current input</button>
            <button class="btn-primary" @click="handleClearInput">Yes, clear input</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Custom Modal: Alert -->
    <Teleport to="body">
      <div v-if="alertModal.show" class="modal-overlay" @click.self="closeAlertModal">
        <div class="modal-dialog alert-dialog" :class="alertModal.type">
          <div class="modal-header">
            <h3>{{ alertModal.title }}</h3>
            <button class="modal-close-button" @click="closeAlertModal">&times;</button>
          </div>
          <div class="modal-body">
            <p>{{ alertModal.message }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn-primary" @click="closeAlertModal">OK</button>
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

const ROUTE_NAMES = {
  HOME: 'home',
} as const

const PYODIDE_CONFIG = {
  INDEX_URL: 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/',
  EXECUTION_TIMEOUT_MS: 5000,
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
    // ==========================================================================
    // ROUTER & VUE FLOW
    // ==========================================================================

    const router = useRouter()
    const { fromObject, toObject, fitView, updateNodeData, getNode } = useVueFlow()

    // ==========================================================================
    // REACTIVE STATE
    // ==========================================================================

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

    // Alert modal state
    const alertModal = ref<AlertModalState>({
      show: false,
      type: 'info',
      title: '',
      message: '',
    })

    // Editor instance reference
    let editorInstance: EditorInstance | null = null

    // Countdown interval reference
    let countdownInterval: ReturnType<typeof setInterval> | null = null

    // Debounce timeout reference
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

    /**
     * Shows a custom alert modal instead of native alert()
     */
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

    /**
     * Closes the alert modal
     */
    const closeAlertModal = (): void => {
      alertModal.value.show = false
    }

    /**
     * Formats a cell value for display in the output table
     */
    const formatCellValue = (value: unknown): string => {
      if (value === null) return 'null'
      if (value === undefined) return 'undefined'
      if (typeof value === 'object') {
        try {
          return JSON.stringify(value)
        } catch {
          return String(value)
        }
      }
      return String(value)
    }

    /**
     * Checks if a value is a PyProxy object
     */
    const isPyProxy = (obj: unknown): obj is PyProxy => {
      return (
        obj !== null &&
        typeof obj === 'object' &&
        'toJs' in obj &&
        typeof (obj as PyProxy).toJs === 'function'
      )
    }

    /**
     * Safely converts a PyProxy to a JavaScript value and destroys the proxy
     */
    const convertPyProxy = (proxy: PyProxy): unknown => {
      try {
        const jsValue = proxy.toJs({ dict_converter: Object.fromEntries })
        return jsValue
      } catch {
        return proxy
      } finally {
        try {
          proxy.destroy()
        } catch {
          // Ignore destruction errors
        }
      }
    }

    /**
     * Clears all Monaco editor error markers
     */
    const clearEditorMarkers = (): void => {
      if (editorInstance && typeof monaco !== 'undefined') {
        const model = editorInstance.getModel()
        if (model) {
          monaco.editor.setModelMarkers(model, 'owner', [])
        }
      }
    }

    /**
     * Sets an error marker in the Monaco editor at the specified line
     */
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

    /**
     * Extracts a line number from a Python error message
     */
    const extractLineNumberFromError = (errorMessage: string): number | null => {
      const match = errorMessage.match(/line\s+(\d+)/i)
      if (match && match[1]) {
        const lineNum = Number.parseInt(match[1], 10)
        const adjustedLine = lineNum - 10
        return adjustedLine > 0 ? adjustedLine : lineNum
      }
      return null
    }

    /**
     * Debug function to inspect nodes
     */
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

    // ==========================================================================
    // NODE MANAGEMENT
    // ==========================================================================

    /**
     * Syncs the current editor content back to the active node's data
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

      // Also update Vue Flow's internal state
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
     * Clears all output state
     */
    const clearOutputs = (): void => {
      consoleOutput.value = ''
      errorOutput.value = ''
      otherOutput.value = ''
      tableOutput.value = false
      tableColumns.value = []
      tableRows.value = []
      runExecuted.value = false
    }

    /**
     * Completes the node switch after user confirms input reset choice
     */
    const completeNodeSwitch = (clearInput: boolean): void => {
      if (!pendingNodeSwitch.value) return

      if (clearInput) {
        inputData.value = ''
      }

      clearOutputs()

      // Load code from the pending node
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
     */
    const handleNodeClick = (event: NodeMouseEvent): void => {
      const clickedNodeId = event.node.id
      const clickedNodeType = event.node.type

      console.log('=== NODE CLICK ===')
      console.log('Clicked node ID:', clickedNodeId)
      console.log('Clicked node type:', clickedNodeType)

      // Only handle transform node clicks
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

      // Clear outputs if we had run before
      if (runExecuted.value) {
        clearOutputs()
      }

      // Find the node in our local nodes array (this has the full data)
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

    /**
     * Handles Monaco editor content changes
     */
    const handleEditorChange = (newValue: string): void => {
      transformationCode.value = newValue
    }

    /**
     * Handles the save code button click
     */
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

    /**
     * Handles the fit view button click
     */
    const handleFitView = (): void => {
      fitView()
    }

    /**
     * Handles Monaco editor mounted event
     */
    const onEditorMounted = (editor: EditorInstance): void => {
      editorInstance = editor
    }

    /**
     * Toggles the sandbox banner visibility
     */
    const toggleSandboxBanner = (): void => {
      showSandboxBanner.value = !showSandboxBanner.value
    }

    // ==========================================================================
    // MODAL HANDLERS
    // ==========================================================================

    /**
     * Closes the reset input confirmation modal
     */
    const closeResetInputModal = (): void => {
      showResetInputConfirm.value = false
      pendingNodeSwitch.value = null
    }

    /**
     * Handles "Keep current input" choice
     */
    const handleKeepInput = (): void => {
      completeNodeSwitch(false)
    }

    /**
     * Handles "Clear input" choice
     */
    const handleClearInput = (): void => {
      completeNodeSwitch(true)
    }

    /**
     * Opens the save confirmation modal
     */
    const handleRequestSaveAndBack = (): void => {
      syncEditorToNode()
      showSaveConfirm.value = true
    }

    /**
     * Closes the save confirmation modal
     */
    const closeSaveConfirmModal = (): void => {
      showSaveConfirm.value = false
    }

    /**
     * Saves the graph and navigates back to HomeView
     */
    const handleSaveAndGoBack = (): void => {
      syncEditorToNode()
      const graph = toObject()
      sessionStorage.setItem(STORAGE_KEYS.GRAPH, JSON.stringify(graph))
      showSaveConfirm.value = false
      router.push({ name: ROUTE_NAMES.HOME })
    }

    /**
     * Discards changes and navigates back to HomeView
     */
    const handleDiscardAndGoBack = (): void => {
      showSaveConfirm.value = false
      router.push({ name: ROUTE_NAMES.HOME })
    }

    // ==========================================================================
    // PYODIDE INITIALIZATION
    // ==========================================================================

    /**
     * Initializes Pyodide with proper stdout/stderr capture
     */
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
          errorOutput.value += text + '\n'
        },
      })

      pyodideInstance = await pyodideLoadPromise
      return pyodideInstance
    }

    // ==========================================================================
    // CODE EXECUTION
    // ==========================================================================

    /**
     * Validates the input JSON
     */
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

    /**
     * Builds the Python wrapper code that executes user code
     */
    const buildPythonWrapper = (userCode: string): string => {
      return `
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', force=True)
logger = logging.getLogger('transform')

# IMPORTANT: Delete any existing transform functions from previous runs
for _name in list(globals().keys()):
    if _name.startswith('transform') or _name in ('main', 'run', 'process'):
        try:
            del globals()[_name]
        except:
            pass

def _convert_to_python(obj):
    if hasattr(obj, 'to_py'):
        return obj.to_py()
    return obj

__js_input = _convert_to_python(__js_input)
if isinstance(__js_input, dict):
    __js_input = dict(__js_input)

${userCode}

_result = None

if 'transform' in dir() and callable(transform):
    _result = transform(__js_input)
elif 'transform1' in dir() and callable(transform1):
    _result = transform1(__js_input)
elif 'transform2' in dir() and callable(transform2):
    _result = transform2(__js_input)
elif 'main' in dir() and callable(main):
    _result = main(__js_input)
elif 'row' in dir():
    _result = row
elif 'output' in dir():
    _result = output
else:
    _result = __js_input

_result
`
    }

    /**
     * Processes the result of Python execution into the appropriate output format
     */
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

      if (Array.isArray(result)) {
        if (result.length === 0) {
          otherOutput.value = '[]'
          return
        }

        const firstItem = result[0]

        if (typeof firstItem === 'object' && firstItem !== null && !Array.isArray(firstItem)) {
          const firstRow = firstItem as Record<string, unknown>
          tableColumns.value = Object.keys(firstRow)
          tableRows.value = result as Record<string, unknown>[]
          tableOutput.value = true
          return
        }

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

    /**
     * Starts the execution countdown timer
     */
    const startCountdown = (): void => {
      executionTimeRemaining.value = PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS / 1000

      countdownInterval = setInterval(() => {
        executionTimeRemaining.value -= 1
        if (executionTimeRemaining.value <= 0) {
          stopCountdown()
        }
      }, 1000)
    }

    /**
     * Stops the execution countdown timer
     */
    const stopCountdown = (): void => {
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
    }

    /**
     * Cancels the current execution
     */
    const cancelExecution = (): void => {
      if (executionAbortController.value) {
        executionAbortController.value.abort()
      }
      stopCountdown()
      isExecuting.value = false
      errorOutput.value = 'Execution cancelled by user.'
      runExecuted.value = true
    }

    /**
     * Runs the transformation code with timeout
     */
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

      syncEditorToNode()

      consoleOutput.value = ''
      errorOutput.value = ''
      otherOutput.value = ''
      tableOutput.value = false
      tableColumns.value = []
      tableRows.value = []
      runExecuted.value = false
      clearEditorMarkers()

      const rawInput = inputData.value.trim()
      const inputObj = validateInputJson(rawInput)
      if (!inputObj) {
        return
      }

      isExecuting.value = true
      executionAbortController.value = new AbortController()
      startCountdown()

      try {
        try {
          pyodideInstance.globals.delete('__js_input')
          pyodideInstance.globals.delete('_result')
          pyodideInstance.globals.delete('_candidate')
          pyodideInstance.globals.delete('_candidate_name')
          pyodideInstance.globals.delete('transform')
          pyodideInstance.globals.delete('transform1')
          pyodideInstance.globals.delete('transform2')
          pyodideInstance.globals.delete('main')
          pyodideInstance.globals.delete('run')
          pyodideInstance.globals.delete('row')
          pyodideInstance.globals.delete('output')
          pyodideInstance.globals.delete('result')
        } catch {
          // Ignore errors when deleting non-existent globals
        }

        pyodideInstance.globals.set('__js_input', inputObj)

        const userCode = transformationCode.value
        console.log('==== CODE BEING EXECUTED ====')
        console.log(userCode)
        console.log('=============================')

        const wrappedCode = buildPythonWrapper(userCode)

        const timeoutPromise = new Promise<never>((_, reject) => {
          const timeoutId = setTimeout(() => {
            reject(
              new Error(
                'Execution timed out after 5 seconds. Your code may contain an infinite loop.',
              ),
            )
          }, PYODIDE_CONFIG.EXECUTION_TIMEOUT_MS)

          executionAbortController.value?.signal.addEventListener('abort', () => {
            clearTimeout(timeoutId)
            reject(new Error('Execution cancelled'))
          })
        })

        let result: unknown = await Promise.race([
          pyodideInstance.runPythonAsync(wrappedCode),
          timeoutPromise,
        ])

        runExecuted.value = true

        if (isPyProxy(result)) {
          result = convertPyProxy(result as PyProxy)
        }

        processExecutionResult(result)

        if (!consoleOutput.value && !otherOutput.value && !tableOutput.value) {
          consoleOutput.value = '(No output, code executed successfully)'
        }

        clearEditorMarkers()
      } catch (err: unknown) {
        runExecuted.value = true

        const errMsg = err instanceof Error ? err.message : String(err)
        errorOutput.value = errMsg

        const lineNumber = extractLineNumberFromError(errMsg)
        if (lineNumber !== null) {
          setEditorErrorMarker(lineNumber, errMsg)
        }
      } finally {
        stopCountdown()
        isExecuting.value = false
        executionAbortController.value = null

        try {
          pyodideInstance?.globals.delete('__js_input')
          pyodideInstance?.globals.delete('_result')
          pyodideInstance?.globals.delete('_candidate')
          pyodideInstance?.globals.delete('_candidate_name')
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

      // Editor state
      transformationCode,
      inputData,
      editingCode,
      activeTransformId,
      monacoEditorRef,
      monacoOptions,

      // UI state
      showSandboxBanner,
      showSaveConfirm,
      showResetInputConfirm,

      // Debug
      debugNodes,

      // Pyodide state
      pyodideLoading,
      pyodideError,

      // Execution state
      isExecuting,
      executionTimeRemaining,

      // Output state
      consoleOutput,
      errorOutput,
      tableOutput,
      tableColumns,
      tableRows,
      otherOutput,
      runExecuted,

      // Alert modal
      alertModal,

      // Computed
      canRun,
      runButtonTooltip,
      activeNodeName,

      // Methods
      handleNodeClick,
      handleSaveCode,
      handleFitView,
      onEditorMounted,
      toggleSandboxBanner,
      handleRunTransformation,
      cancelExecution,

      // Modal handlers
      closeAlertModal,
      closeResetInputModal,
      handleKeepInput,
      handleClearInput,
      handleEditorChange,
      handleRequestSaveAndBack,
      closeSaveConfirmModal,
      handleSaveAndGoBack,
      handleDiscardAndGoBack,

      // Utilities
      formatCellValue,
    }
  },
})
</script>

<style scoped>
/* ============================================================================
   LAYOUT
   ============================================================================ */

.test-area {
  display: flex;
  height: 100vh;
  color: #f0f0f0;
  background: #1e1e1e;
  position: relative;
}

.left-panel {
  width: 35%;
  min-width: 350px;
  max-width: 500px;
  background: #252526;
  padding: 0.75rem;
  overflow: auto;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #3c3c3c;
}

.center-panel {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ============================================================================
   LOADING OVERLAYS
   ============================================================================ */

.loading-overlay,
.execution-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.loading-content,
.execution-content {
  text-align: center;
  color: #fff;
}

.loading-content h3,
.execution-content h3 {
  margin: 1rem 0 0.5rem;
  font-size: 1.5rem;
}

.loading-content p,
.execution-content p {
  margin: 0;
  color: #aaa;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.cancel-button {
  margin-top: 1.5rem;
  padding: 0.5rem 1.5rem;
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.cancel-button:hover {
  background: #dc2626;
}

/* ============================================================================
   INPUT SECTION
   ============================================================================ */

.input-section {
  margin-bottom: 0.75rem;
}

.input-section h3 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: #ccc;
}

.input-section textarea {
  width: 100%;
  min-height: 80px;
  max-height: 150px;
  background: #1a1a1a;
  color: #f0f0f0;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
  padding: 0.5rem;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}

.input-section textarea:focus {
  outline: none;
  border-color: #3b82f6;
}

.input-section textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ============================================================================
   EDITOR PANE
   ============================================================================ */

.editor-pane {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e1e1e;
  padding: 0.5rem 0.75rem;
  border-radius: 4px 4px 0 0;
  border: 1px solid #3c3c3c;
  border-bottom: none;
}

.editor-title {
  font-size: 0.85rem;
  color: #aaa;
}

.editor-title strong {
  color: #fff;
}

.editor-title .no-selection {
  color: #666;
  font-style: italic;
}

.save-code-button {
  background: #3b82f6;
  color: #fff;
  border: none;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.2s;
}

.save-code-button:hover:not(:disabled) {
  background: #2563eb;
}

.save-code-button:disabled {
  background: #4b5563;
  cursor: not-allowed;
  opacity: 0.6;
}

/* ============================================================================
   EDITOR PLACEHOLDER
   ============================================================================ */

.editor-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  border: 1px solid #3c3c3c;
  border-top: none;
  min-height: 200px;
}

.placeholder-content {
  text-align: center;
  padding: 2rem;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.placeholder-content h3 {
  margin: 0 0 0.5rem;
  color: #888;
  font-size: 1.1rem;
}

.placeholder-content p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.placeholder-content strong {
  color: #3b82f6;
}

/* ============================================================================
   MONACO EDITOR
   ============================================================================ */

.monaco-editor {
  flex: 1;
  min-height: 200px;
  border: 1px solid #3c3c3c;
  border-top: none;
}

/* ============================================================================
   RUN SECTION
   ============================================================================ */

.run-section {
  margin-top: 0.75rem;
}

.run-button {
  width: 100%;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  border: none;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
}

.run-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #16a34a, #15803d);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4);
}

.run-button:disabled {
  background: #4b5563;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.button-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* ============================================================================
   OUTPUT SECTION
   ============================================================================ */

.output-section {
  margin-top: 0.75rem;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  overflow: hidden;
}

.output-title {
  margin: 0;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  background: #111827;
  border-bottom: 1px solid #3c3c3c;
}

.results-pane {
  padding: 0.75rem;
  background: #1a1a1a;
}

.validation-message {
  font-size: 0.95rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
}

.validation-message.success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.validation-message.error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.console-output-section h3,
.error-output-section h3,
.table-output-section h3,
.other-output-section h3 {
  margin: 0;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  background: #252526;
  color: #aaa;
}

.console-output,
.error-output,
.other-output {
  margin: 0;
  padding: 0.75rem;
  background: #0a0a0a;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.console-output {
  color: #4ade80;
}

.error-output {
  color: #f87171;
}

.other-output {
  color: #60a5fa;
}

/* ============================================================================
   TABLE OUTPUT
   ============================================================================ */

.table-wrapper {
  max-height: 300px;
  overflow: auto;
}

.output-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.output-table th,
.output-table td {
  border: 1px solid #3c3c3c;
  padding: 0.4rem 0.6rem;
  text-align: left;
}

.output-table th {
  background: #1e293b;
  color: #94a3b8;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.output-table td {
  background: #0f172a;
  color: #e2e8f0;
}

.output-table tr:hover td {
  background: #1e293b;
}

/* ============================================================================
   SANDBOX HEADER & BANNER
   ============================================================================ */

.sandbox-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: linear-gradient(90deg, #0f172a, #1d4ed8, #06b6d4);
  box-shadow: 0 0 15px rgba(37, 99, 235, 0.4);
}

.sandbox-title {
  font-size: 14px;
  font-weight: 600;
  color: #e5f2ff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.sandbox-title > span:first-of-type {
  color: #a5f3fc;
}

.pyodide-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.pyodide-status.loading {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.pyodide-status.ready {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.pyodide-status.error {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.sandbox-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sandbox-toggle {
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(226, 232, 240, 0.5);
  background: rgba(15, 23, 42, 0.6);
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sandbox-toggle:hover {
  background: rgba(15, 23, 42, 0.9);
  transform: translateY(-1px);
}

.sandbox-back {
  font-size: 12px;
  padding: 5px 14px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(90deg, #22c55e, #16a34a);
  color: #e5fdf5;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
  transition: all 0.15s ease;
}

.sandbox-back:hover:not(:disabled) {
  background: linear-gradient(90deg, #4ade80, #22c55e);
  transform: translateY(-1px);
}

.sandbox-back:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.sandbox-banner {
  background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.2), rgba(15, 23, 42, 0.95));
  border: 1px solid rgba(59, 130, 246, 0.5);
  color: #e0f2fe;
  padding: 10px 14px;
  margin-bottom: 10px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}

/* ============================================================================
   VUE FLOW
   ============================================================================ */

.test-flow {
  flex: 1;
  border: 1px solid #3c3c3c;
  border-radius: 8px;
  background: #0f172a;
}

.panel-info {
  background: rgba(0, 0, 0, 0.7);
  padding: 6px 10px;
  border-radius: 6px;
  color: #cbd5e1;
}

/* ============================================================================
   MODAL STYLES
   ============================================================================ */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-dialog {
  width: 100%;
  max-width: 450px;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border-radius: 12px;
  box-shadow: 0 0 30px rgba(37, 99, 235, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.6);
  color: #e5f0ff;
  animation: slideIn 0.2s ease;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #f0f9ff;
}

.modal-close-button {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.15s;
}

.modal-close-button:hover {
  color: #fff;
}

.modal-body {
  padding: 20px;
}

.modal-body p {
  margin: 0;
  color: #cbd5e1;
  font-size: 0.95rem;
  line-height: 1.5;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.3);
}

.btn-primary,
.btn-secondary {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
  border: none;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(15, 23, 42, 0.8);
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.5);
}

.btn-secondary:hover {
  background: rgba(30, 41, 59, 0.9);
  transform: translateY(-1px);
}

/* Alert modal type variants */
.alert-dialog.warning .modal-header {
  border-bottom-color: rgba(251, 191, 36, 0.4);
}

.alert-dialog.warning .modal-header h3 {
  color: #fbbf24;
}

.alert-dialog.error .modal-header {
  border-bottom-color: rgba(239, 68, 68, 0.4);
}

.alert-dialog.error .modal-header h3 {
  color: #f87171;
}

/* ============================================================================
   RESPONSIVE ADJUSTMENTS
   ============================================================================ */

@media (max-width: 1024px) {
  .left-panel {
    width: 40%;
    min-width: 300px;
  }
}

@media (max-width: 768px) {
  .test-area {
    flex-direction: column;
  }

  .left-panel {
    width: 100%;
    max-width: none;
    height: 50vh;
    border-right: none;
    border-bottom: 1px solid #3c3c3c;
  }

  .center-panel {
    height: 50vh;
  }
}
</style>
