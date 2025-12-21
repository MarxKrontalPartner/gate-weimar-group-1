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
      <div class="input-section">
        <h3>Input Data:</h3>
        <textarea
          v-model="inputData"
          placeholder='{"channel_1":1, "channel_2":2}'
          :disabled="isExecuting"
        ></textarea>
      </div>

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
          <button
            class="debug-button"
            @click="handleDebugCode"
            :disabled="!activeTransformId || isExecuting"
            title="Check code for errors and highlight issues"
          >
            🔍 Debug
          </button>
        </div>

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
      <div class="sandbox-header">
        <div class="sandbox-title">
          Test Area · <span>Sandbox</span>
          <span v-if="pyodideLoading" class="pyodide-status loading">⏳ Loading Python...</span>
          <span v-else-if="pyodideError" class="pyodide-status error">❌ Python Error</span>
          <span v-else class="pyodide-status ready">✅ Python Ready</span>
        </div>
        <div class="sandbox-actions">
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
        <!-- Reusable node templates -->
        <template #node-custom-input="nodeProps">
          <CustomInputNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>
        <template #node-custom-output="nodeProps">
          <CustomOutputNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>
        <template #node-custom-transform="nodeProps">
          <CustomTransformNode :id="nodeProps.id" :data="nodeProps.data" />
        </template>
        <template #node-custom-intermediate="nodeProps">
          <CustomIntermediateNode :id="nodeProps.id" :data="nodeProps.data" />
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

    <Teleport to="body">
      <div v-if="alertModal.show" class="testarea-modal-overlay" @click.self="closeAlertModal">
        <div class="testarea-modal-dialog testarea-alert-dialog" :class="alertModal.type">
          <div class="testarea-modal-header">
            <h3>{{ alertModal.title }}</h3>
            <button class="testarea-modal-close-button" @click="closeAlertModal">&times;</button>
          </div>
          <div class="testarea-modal-body">
            <p style="white-space: pre-wrap">{{ alertModal.message }}</p>
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
import CustomIntermediateNode from '@/components/CustomIntermediateNode.vue'
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
  revealLineInCenter: (lineNumber: number) => void
  setPosition: (position: { lineNumber: number; column: number }) => void
}

interface EditorModel {
  getLineLength: (lineNumber: number) => number
  getLineCount: () => number
  getValue: () => string
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
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
}

interface PyodideConfig {
  INDEX_URL: string
  EXECUTION_TIMEOUT_MS: number
}

// ============================================================================
// CONSTANTS
// ============================================================================

const NODE_TYPES = {
  INPUT: 'custom-input',
  TRANSFORM: 'custom-transform',
  OUTPUT: 'custom-output',
  INTERMEDIATE: 'custom-intermediate',
} as const

const STORAGE_KEYS = {
  GRAPH: 'testarea_graph',
} as const

const ROUTE_NAMES = {
  HOME: 'home',
  TEST_AREA: 'test-area',
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

const getPyodideConfig = (): PyodideConfig => {
  const windowConfig = (window as unknown as { PYODIDE_CONFIG?: PyodideConfig }).PYODIDE_CONFIG
  return (
    windowConfig || {
      INDEX_URL: 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/',
      EXECUTION_TIMEOUT_MS: 30000,
    }
  )
}

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
    CustomIntermediateNode,
  },

  setup() {
    const router = useRouter()
    const { fromObject, toObject, fitView, updateNodeData } = useVueFlow()

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

    // Pyodide state
    const pyodideLoading = ref<boolean>(true)
    const pyodideError = ref<string | null>(null)

    // Execution state
    const isExecuting = ref<boolean>(false)
    const executionTimeRemaining = ref<number>(30)
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

    // Debug state - stores last error info
    const lastErrorInfo = ref<{ line: number; message: string; suggestion: string } | null>(null)

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
      if (pyodideLoading.value) return 'Python runtime is still loading...'
      if (pyodideError.value) return 'Python runtime failed to load'
      if (!activeTransformId.value) return 'Select a Transform node first'
      if (transformationCode.value.trim().length === 0) return 'Enter some code to run'
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
      type: 'info' | 'warning' | 'error' | 'success' = 'info',
    ): void => {
      alertModal.value = { show: true, type, title, message }
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
      lastErrorInfo.value = null
    }

    const setEditorErrorMarker = (lineNumber: number, message: string): void => {
      if (editorInstance && typeof monaco !== 'undefined') {
        const model = editorInstance.getModel()
        if (model && Number.isFinite(lineNumber) && lineNumber > 0) {
          const maxLine = model.getLineCount()
          const actualLine = Math.min(lineNumber, maxLine)
          const endColumn = model.getLineLength(actualLine) + 1

          monaco.editor.setModelMarkers(model, 'owner', [
            {
              startLineNumber: actualLine,
              startColumn: 1,
              endLineNumber: actualLine,
              endColumn,
              message,
              severity: monaco.MarkerSeverity.Error,
            },
          ])

          editorInstance.revealLineInCenter(actualLine)
          editorInstance.setPosition({ lineNumber: actualLine, column: 1 })
        }
      }
    }

    // Count the lines in the wrapper code BEFORE user code
    // The wrapper has ~54 lines before ${userCode} is inserted
    const WRAPPER_LINES_BEFORE_USER_CODE = 54

    const extractLineNumberFromError = (errorMessage: string): number | null => {
      const execPattern = /File\s+["']<(?:exec|string|module)>["'],\s*line\s+(\d+)/gi
      const execMatches = [...errorMessage.matchAll(execPattern)]

      if (execMatches.length > 0) {
        const lastMatch = execMatches[execMatches.length - 1]
        if (lastMatch && lastMatch[1]) {
          const lineNum = Number.parseInt(lastMatch[1], 10)
          const adjustedLine = lineNum - WRAPPER_LINES_BEFORE_USER_CODE
          return adjustedLine > 0 ? adjustedLine : 1
        }
      }

      const linePattern = /line\s+(\d+)/gi
      const allLineMatches = [...errorMessage.matchAll(linePattern)]

      if (allLineMatches.length > 0) {
        const reasonableMatches = allLineMatches.filter((m) => {
          const num = Number.parseInt(m[1] || '0', 10)
          return num > WRAPPER_LINES_BEFORE_USER_CODE && num < WRAPPER_LINES_BEFORE_USER_CODE + 500
        })

        if (reasonableMatches.length > 0) {
          const lastMatch = reasonableMatches[reasonableMatches.length - 1]
          if (lastMatch && lastMatch[1]) {
            const lineNum = Number.parseInt(lastMatch[1], 10)
            const adjustedLine = lineNum - WRAPPER_LINES_BEFORE_USER_CODE
            return adjustedLine > 0 ? adjustedLine : 1
          }
        }

        const lastMatch = allLineMatches[allLineMatches.length - 1]
        if (lastMatch && lastMatch[1]) {
          const lineNum = Number.parseInt(lastMatch[1], 10)
          const adjustedLine = lineNum - WRAPPER_LINES_BEFORE_USER_CODE
          return adjustedLine > 0 ? adjustedLine : null
        }
      }

      const syntaxPattern = /SyntaxError.*line\s+(\d+)/i
      const syntaxMatch = errorMessage.match(syntaxPattern)
      if (syntaxMatch && syntaxMatch[1]) {
        const lineNum = Number.parseInt(syntaxMatch[1], 10)
        const adjustedLine = lineNum - WRAPPER_LINES_BEFORE_USER_CODE
        return adjustedLine > 0 ? adjustedLine : 1
      }

      return null
    }

    const extractErrorContext = (errorMessage: string): string => {
      const lines = errorMessage.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i] || ''
        if (line.startsWith('    ') && !line.includes('File ') && !line.includes('Traceback')) {
          const codeLine = line.trim()
          if (codeLine && !codeLine.startsWith('^') && codeLine.length > 2) {
            return codeLine
          }
        }
      }
      return ''
    }

    const generateErrorSuggestion = (errorMessage: string): string => {
      const suggestions: Array<{ pattern: RegExp; suggestion: string }> = [
        {
          pattern: /SyntaxError.*unexpected EOF/i,
          suggestion: 'Check for missing closing brackets, parentheses, or incomplete statements.',
        },
        {
          pattern: /IndentationError.*unexpected indent/i,
          suggestion:
            'This line has extra indentation. Remove extra spaces at the beginning of the line.',
        },
        {
          pattern: /IndentationError.*expected an indented block/i,
          suggestion:
            'Add indented code after this statement. Python requires code inside if/for/while/def blocks.',
        },
        {
          pattern: /IndentationError/i,
          suggestion:
            'Check your indentation. Python uses 4 spaces for each indentation level. Make sure all lines in a block have consistent indentation.',
        },
        {
          pattern: /NameError.*'(\w+)'.*not defined/i,
          suggestion:
            'The variable or function "$1" is not defined. Check for typos or define it before use.',
        },
        {
          pattern: /NameError.*not defined/i,
          suggestion:
            'The variable or function is not defined. Check for typos or define it before use.',
        },
        {
          pattern: /TypeError.*takes \d+ positional argument/i,
          suggestion:
            'Wrong number of arguments passed to the function. Check the function definition.',
        },
        {
          pattern: /TypeError.*argument/i,
          suggestion: 'Check the number and types of arguments passed to the function.',
        },
        {
          pattern: /KeyError.*'(\w+)'/i,
          suggestion:
            'The key "$1" does not exist in the dictionary. Use .get("$1", default) or check if key exists first.',
        },
        {
          pattern: /KeyError/i,
          suggestion:
            'The dictionary key does not exist. Use .get() method or check if key exists first.',
        },
        {
          pattern: /AttributeError.*'(\w+)'.*no attribute.*'(\w+)'/i,
          suggestion:
            'The object of type "$1" does not have attribute "$2". Check the object type and available methods.',
        },
        {
          pattern: /AttributeError/i,
          suggestion:
            'The object does not have this attribute. Check the object type and available methods.',
        },
        {
          pattern: /SyntaxError.*invalid syntax.*#/i,
          suggestion:
            'Remove the # comment marker if you want this line to execute, or fix the syntax before the comment.',
        },
        {
          pattern: /SyntaxError.*invalid syntax/i,
          suggestion:
            'Check for missing colons (:), incorrect operators, mismatched quotes, or incomplete statements.',
        },
        {
          pattern: /SyntaxError.*expected ':'/i,
          suggestion: 'Add a colon (:) at the end of if/else/for/while/def/class statements.',
        },
        {
          pattern: /SyntaxError.*EOL while scanning string/i,
          suggestion: 'You have an unclosed string. Make sure all quotes are properly matched.',
        },
        {
          pattern: /ZeroDivisionError/i,
          suggestion: 'Division by zero occurred. Add a check to ensure the divisor is not zero.',
        },
        {
          pattern: /IndexError.*out of range/i,
          suggestion:
            'List index is out of range. Check that the index exists before accessing it.',
        },
        {
          pattern: /ValueError/i,
          suggestion: 'Invalid value for the operation. Check the input data types and values.',
        },
        {
          pattern: /ImportError|ModuleNotFoundError/i,
          suggestion:
            'Module not found. Only standard library modules are available in the sandbox.',
        },
      ]

      for (const { pattern, suggestion } of suggestions) {
        const match = errorMessage.match(pattern)
        if (match) {
          let result = suggestion
          if (match[1]) result = result.replace('$1', match[1])
          if (match[2]) result = result.replace('$2', match[2])
          return result
        }
      }

      return 'Review the error message and check your code syntax.'
    }

    const syncEditorToNode = (): void => {
      if (!activeTransformId.value) return

      const nodeIndex = nodes.value.findIndex((n) => n.id === activeTransformId.value)
      if (nodeIndex === -1) return

      const currentNode = nodes.value[nodeIndex]
      if (!currentNode) return

      const currentData = (currentNode.data || {}) as TransformNodeData

      nodes.value[nodeIndex] = {
        ...currentNode,
        data: {
          ...currentData,
          code: transformationCode.value,
        },
      }

      updateNodeData(activeTransformId.value, {
        ...currentData,
        code: transformationCode.value,
      })
    }

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
      chartOutput.value = false
      chartTitle.value = 'Chart'
      destroyChart()
      runExecuted.value = false
      clearEditorMarkers()
    }

    // ==========================================================================
    // DEBUG FUNCTIONALITY
    // ==========================================================================

    const handleDebugCode = (): void => {
      if (!activeTransformId.value) {
        showAlert('No Transform Selected', 'Please select a transform node first.', 'warning')
        return
      }

      if (lastErrorInfo.value) {
        const { line, message, suggestion } = lastErrorInfo.value

        setEditorErrorMarker(line, message)

        showAlert(
          '🔍 Error Found',
          `📍 Line ${line}: ${message}\n\n💡 Suggestion:\n${suggestion}`,
          'error',
        )
        return
      }

      // If there's error output from last run
      if (errorOutput.value) {
        const lineNumber = extractLineNumberFromError(errorOutput.value)
        const suggestion = generateErrorSuggestion(errorOutput.value)
        const codeContext = extractErrorContext(errorOutput.value)

        const errorLines = errorOutput.value.split('\n')
        let shortError = ''
        for (const errLine of errorLines) {
          if (errLine.includes('Error:') || errLine.includes('Exception:')) {
            shortError = errLine.trim()
            break
          }
        }
        if (!shortError) {
          shortError = errorLines[errorLines.length - 1]?.trim() || 'Unknown error'
        }

        if (lineNumber && lineNumber > 0) {
          setEditorErrorMarker(lineNumber, shortError)

          let message = `📍 Line ${lineNumber}: ${shortError}`
          if (codeContext) {
            message += `\n\n📝 Problematic code:\n   ${codeContext}`
          }
          message += `\n\n💡 Suggestion:\n${suggestion}`

          showAlert('🔍 Error Found', message, 'error')
        } else {
          showAlert('🔍 Error Found', `${shortError}\n\n💡 Suggestion:\n${suggestion}`, 'error')
        }
        return
      }

      clearEditorMarkers()
      showAlert(
        '✅ No Errors Found',
        'The code appears to be syntactically correct.\n\nRun the transformation to test its functionality.',
        'success',
      )
    }

    // ==========================================================================
    // EVENT HANDLERS
    // ==========================================================================

    const handleNodeClick = (event: NodeMouseEvent): void => {
      const clickedNodeId = event.node.id
      const clickedNodeType = event.node.type

      if (clickedNodeType !== NODE_TYPES.TRANSFORM) {
        return
      }

      if (activeTransformId.value === clickedNodeId) {
        return
      }

      if (activeTransformId.value) {
        syncEditorToNode()
      }
      clearOutputs()

      const targetNode = nodes.value.find((n) => n.id === clickedNodeId)

      if (targetNode && targetNode.data) {
        const nodeData = targetNode.data as TransformNodeData
        activeTransformId.value = clickedNodeId
        transformationCode.value = nodeData.code || ''
        editingCode.value = true
      } else {
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
      if (pyodideInstance) return pyodideInstance
      if (pyodideLoadPromise) return pyodideLoadPromise

      const config = getPyodideConfig()

      pyodideLoadPromise = loadPyodide({
        indexURL: config.INDEX_URL,
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

_stdout_buffer = StringIO()
_stderr_buffer = StringIO()
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = _stdout_buffer
sys.stderr = _stderr_buffer

class Logger:
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def warn(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")
    def debug(self, msg): print(f"DEBUG: {msg}")

logger = Logger()

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

_functions_before = {k for k, v in globals().items() if callable(v)}

${userCode}

_functions_after = {
    k for k, v in globals().items()
    if callable(v) and not k.startswith('_') and k != 'Logger'
}
_user_functions = _functions_after - _functions_before

_result = None
_function_found = False
_tried_functions = []

_priority_names = ['transform', 'main', 'process', 'run', 'execute', 'handle', 'compute']

for _fname in _priority_names:
    if _fname in globals() and callable(globals()[_fname]):
        _tried_functions.append(_fname)
        try:
            _result = globals()[_fname](_input_data)
            _function_found = True
            break
        except Exception as e:
            print(f"Error calling {_fname}: {e}")

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

sys.stdout = _original_stdout
sys.stderr = _original_stderr

_captured_stdout = _stdout_buffer.getvalue()
_captured_stderr = _stderr_buffer.getvalue()

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

    const renderChart = async (chartData: Record<string, unknown>): Promise<void> => {
      destroyChart()

      const chartType = (chartData.chart_type as string) || 'bar'
      const title = (chartData.title as string) || 'Chart'
      const data = chartData.data as Record<string, unknown>[]

      if (!data || !Array.isArray(data)) return

      chartTitle.value = title
      chartOutput.value = true

      await nextTick()
      await new Promise((resolve) => setTimeout(resolve, 100))

      if (!chartCanvas.value) return

      const ctx = chartCanvas.value.getContext('2d')
      if (!ctx) return

      let config: ChartConfiguration

      if (chartType === 'pie' || chartType === 'doughnut') {
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
            },
          },
        }
      } else if (chartType === 'scatter') {
        const points = data.map((d) => ({ x: Number(d.x || 0), y: Number(d.y || 0) }))

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
            plugins: { legend: { labels: { color: '#e2e8f0' } } },
          },
        }
      } else {
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
              x: { grid: { color: 'rgba(148, 163, 184, 0.2)' }, ticks: { color: '#94a3b8' } },
              y: { grid: { color: 'rgba(148, 163, 184, 0.2)' }, ticks: { color: '#94a3b8' } },
            },
            plugins: { legend: { labels: { color: '#e2e8f0' } } },
          },
        }
      }

      try {
        chartInstance = new ChartJS(ctx, config)
      } catch (chartError) {
        chartOutput.value = false
        chartTitle.value = ''
        throw chartError
      }
    }

    const generateColors = (count: number): string[] => {
      const baseColors: readonly string[] = [
        'rgba(59, 130, 246, 0.7)',
        'rgba(34, 197, 94, 0.7)',
        'rgba(249, 115, 22, 0.7)',
        'rgba(168, 85, 247, 0.7)',
        'rgba(236, 72, 153, 0.7)',
        'rgba(20, 184, 166, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(99, 102, 241, 0.7)',
        'rgba(16, 185, 129, 0.7)',
      ] as const
      const colors: string[] = []
      for (let i = 0; i < count; i++) {
        const color = baseColors[i % baseColors.length]
        if (color) colors.push(color)
      }
      return colors
    }

    const isChartData = (result: unknown): result is Record<string, unknown> => {
      if (typeof result !== 'object' || result === null || Array.isArray(result)) return false
      const obj = result as Record<string, unknown>
      return 'chart_type' in obj && 'data' in obj && Array.isArray(obj.data)
    }

    const getExplicitOutputType = (result: unknown): string | null => {
      if (typeof result !== 'object' || result === null || Array.isArray(result)) return null
      const obj = result as Record<string, unknown>
      if ('output_type' in obj && typeof obj.output_type === 'string')
        return obj.output_type.toLowerCase()
      return null
    }

    const extractResultData = (result: Record<string, unknown>): unknown => {
      if ('data' in result) return result.data
      const copy = { ...result }
      delete copy.output_type
      return copy
    }

    const processExecutionResult = (result: unknown): void => {
      if (result === null || result === undefined) {
        if (!consoleOutput.value)
          consoleOutput.value = '(No output value, code executed successfully)'
        return
      }

      if (typeof result === 'string') {
        otherOutput.value = result
        return
      }

      const explicitType = getExplicitOutputType(result)

      if (explicitType === 'json') {
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
        renderChart(result as Record<string, unknown>).catch((err) => {
          console.error('Failed to render chart:', err)
          chartOutput.value = false
          chartTitle.value = ''
          otherOutput.value = JSON.stringify(result, null, 2)
        })
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

    const startCountdown = (): void => {
      const config = getPyodideConfig()
      executionTimeRemaining.value = config.EXECUTION_TIMEOUT_MS / 1000

      countdownInterval = setInterval(() => {
        executionTimeRemaining.value -= 1
        if (executionTimeRemaining.value <= 0) stopCountdown()
      }, 1000)
    }

    const stopCountdown = (): void => {
      if (countdownInterval) {
        clearInterval(countdownInterval)
        countdownInterval = null
      }
    }

    const cancelExecution = (): void => {
      if (executionAbortController.value) executionAbortController.value.abort()
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
      ]

      for (const name of globalsToDelete) {
        try {
          pyodideInstance.globals.delete(name)
        } catch {
          /* ignore */
        }
      }
    }

    const handleRunTransformation = async (): Promise<void> => {
      if (!pyodideInstance) {
        showAlert(
          'Python Not Ready',
          'The Python runtime is still loading. Please wait.',
          'warning',
        )
        return
      }

      if (!activeTransformId.value) {
        showAlert('No Transform Selected', 'Please click on a Transform node first.', 'warning')
        return
      }

      syncEditorToNode()

      // Clear all outputs
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
      if (!inputObj) return

      isExecuting.value = true
      executionAbortController.value = new AbortController()
      startCountdown()

      try {
        clearPyodideGlobals()
        pyodideInstance.globals.set('__js_input', inputObj)

        const userCode = transformationCode.value
        const wrappedCode = buildPythonWrapper(userCode)

        const config = getPyodideConfig()
        const timeoutPromise = new Promise<never>((_, reject) => {
          const timeoutId = setTimeout(() => {
            reject(
              new Error(`Execution timed out after ${config.EXECUTION_TIMEOUT_MS / 1000} seconds.`),
            )
          }, config.EXECUTION_TIMEOUT_MS)

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

        const result = deepConvertToJS(rawResult) as {
          result?: unknown
          stdout?: string
          stderr?: string
          function_found?: boolean
          tried_functions?: string[]
          user_functions?: string[]
        } | null

        if (result && typeof result === 'object') {
          if (result.stdout) consoleOutput.value += result.stdout
          if (result.stderr && result.stderr.trim()) errorOutput.value += result.stderr

          if (!result.function_found) {
            consoleOutput.value +=
              '\n⚠️ No transform function found. Define a function like:\n' +
              'def transform(row: dict) -> dict:\n' +
              '    # your code here\n' +
              '    return row\n'
          }

          const actualResult = deepConvertToJS(result.result)
          processExecutionResult(actualResult)
        } else {
          processExecutionResult(result)
        }

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

        // Store error info for debug button
        const lineNumber = extractLineNumberFromError(errMsg)
        const codeContext = extractErrorContext(errMsg)

        // Extract clean error message
        const errorLines = errMsg.split('\n')
        let shortError = ''
        for (const errLine of errorLines) {
          if (errLine.includes('Error:') || errLine.includes('Exception:')) {
            shortError = errLine.trim()
            break
          }
        }
        if (!shortError) {
          shortError = errorLines[errorLines.length - 1]?.trim() || errMsg.split('\n')[0] || 'Error'
        }

        if (lineNumber !== null && lineNumber > 0) {
          lastErrorInfo.value = {
            line: lineNumber,
            message: shortError + (codeContext ? `\nCode: ${codeContext}` : ''),
            suggestion: generateErrorSuggestion(errMsg),
          }
          setEditorErrorMarker(lineNumber, shortError)
        }
      } finally {
        stopCountdown()
        isExecuting.value = false
        executionAbortController.value = null

        try {
          pyodideInstance?.globals.delete('__js_input')
        } catch {
          /* ignore */
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

          if (graph.nodes && Array.isArray(graph.nodes)) {
            nodes.value = graph.nodes as Node[]
          }
          if (graph.edges && Array.isArray(graph.edges)) {
            edges.value = graph.edges as Edge[]
          }

          fromObject(graph)
          await nextTick()
        } catch (e) {
          console.error('Error parsing stored graph for TestArea:', e)
        }
      }

      try {
        await initializePyodide()
        pyodideLoading.value = false
        pyodideError.value = null
      } catch (err) {
        pyodideLoading.value = false
        pyodideError.value = err instanceof Error ? err.message : String(err)
      }
    })

    onUnmounted(() => {
      stopCountdown()
      if (executionAbortController.value) executionAbortController.value.abort()
      clearEditorMarkers()
      destroyChart()
      if (saveDebounceTimeout) clearTimeout(saveDebounceTimeout)
    })

    // ==========================================================================
    // WATCHERS
    // ==========================================================================

    watch(transformationCode, () => {
      if (saveDebounceTimeout) clearTimeout(saveDebounceTimeout)

      saveDebounceTimeout = setTimeout(() => {
        if (activeTransformId.value) syncEditorToNode()
      }, 1000)
    })

    // ==========================================================================
    // RETURN
    // ==========================================================================

    return {
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
      handleDebugCode,
      cancelExecution,
      closeAlertModal,
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

<style>
/* Styles are in testarea-styles.css */
</style>
