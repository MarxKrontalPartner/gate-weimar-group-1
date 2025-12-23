<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { CodeEditor } from 'monaco-editor-vue3'
import UIkit from 'uikit'

interface Props {
  show: boolean
  nodeName: string
  initialCode: string
  isDark: boolean
}

interface PyodideInterface {
  globals: { set: (n: string, v: unknown) => void; delete: (n: string) => void }
  runPythonAsync: (code: string) => Promise<unknown>
}

interface PyProxy {
  toJs: (opts?: { dict_converter?: (e: Iterable<[string, unknown]>) => unknown }) => unknown
  destroy: () => void
}

declare const loadPyodide: (opts?: { indexURL?: string }) => Promise<PyodideInterface>
declare const monaco: { editor: { setModelMarkers: (m: unknown, o: string, markers: unknown[]) => void }; MarkerSeverity: { Error: number } } | undefined

let pyodide: PyodideInterface | null = null
let pyodidePromise: Promise<PyodideInterface> | null = null

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'save', code: string): void }>()

const code = ref('')
const originalCode = ref('')
const inputData = ref('')
const isExecuting = ref(false)
const hasRun = ref(false)
const pyodideReady = ref(false)
const pyodideLoading = ref(true)
const editorRef = ref<{ editor: unknown } | null>(null)

const output = ref<{ result?: unknown; console?: string; error?: { msg: string; line: number | null; hint: string } } | null>(null)

const editorOptions = computed(() => ({
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  tabSize: 4,
}))

const canRun = computed(() => pyodideReady.value && code.value.trim() && !isExecuting.value)
const userCodeLineCount = computed(() => code.value.split('\n').length)

watch(() => props.show, (v) => {
  if (v) {
    code.value = props.initialCode
    originalCode.value = props.initialCode
    inputData.value = ''
    hasRun.value = false
    output.value = null
    clearMarkers()
    initPyodide()
  }
})

async function initPyodide() {
  if (pyodide) { pyodideReady.value = true; pyodideLoading.value = false; return }
  if (pyodidePromise) { await pyodidePromise; return }
  pyodideLoading.value = true
  try {
    pyodidePromise = loadPyodide()
    pyodide = await pyodidePromise
    pyodideReady.value = true
  } catch { pyodideReady.value = false }
  pyodideLoading.value = false
}

function isPyProxy(o: unknown): o is PyProxy {
  return o !== null && typeof o === 'object' && 'toJs' in o
}

function toJS(o: unknown): unknown {
  if (o == null) return o
  if (isPyProxy(o)) { const c = o.toJs({ dict_converter: Object.fromEntries }); o.destroy(); return toJS(c) }
  if (o instanceof Map) { const r: Record<string, unknown> = {}; o.forEach((v, k) => r[String(k)] = toJS(v)); return r }
  if (Array.isArray(o)) return o.map(toJS)
  if (typeof o === 'object') { const r: Record<string, unknown> = {}; for (const [k, v] of Object.entries(o)) r[k] = toJS(v); return r }
  return o
}

function escapeForPython(str: string): string {
  return str.replace(/\\/g, '\\\\').replace(/'''/g, "\\'\\'\\'")
}

function buildExecutionCode(userCode: string): string {
  const escaped = escapeForPython(userCode)
  return `
import sys, traceback, ast
from io import StringIO

_user_code = '''${escaped}'''
_result = {"output": None, "stdout": "", "error": None}
_stdout_capture = StringIO()
_original_stdout = sys.stdout

class Logger:
    def info(self, m): print(f"INFO: {m}")
    def warning(self, m): print(f"WARN: {m}")
    def error(self, m): print(f"ERROR: {m}")
    def debug(self, m): print(f"DEBUG: {m}")

def _to_dict(o):
    if hasattr(o, 'to_py'): o = o.to_py()
    return dict(o) if isinstance(o, dict) else o

try:
    ast.parse(_user_code)
except SyntaxError as e:
    _result["error"] = {"type": "SyntaxError", "msg": e.msg or str(e), "line": e.lineno}
else:
    sys.stdout = _stdout_capture
    _exec_globals = {"__builtins__": __builtins__, "logger": Logger(), "_input": _to_dict(__input_data)}

    try:
        exec(compile(_user_code, '<user>', 'exec'), _exec_globals)

        _builtin = set(dir(__builtins__)) | {'logger', '_input', '__builtins__'}
        _funcs = [n for n in _exec_globals if callable(_exec_globals.get(n)) and not n.startswith('_') and n not in _builtin]
        _priority = ['transform', 'main', 'process', 'run', 'execute', 'compute', 'handle']
        _target = None

        for p in _priority:
            for f in _funcs:
                if f == p or f.startswith(p):
                    _target = f
                    break
            if _target: break

        if not _target and _funcs:
            _target = _funcs[0]

        if _target:
            _result["output"] = _exec_globals[_target](_exec_globals.get('_input'))

    except Exception as e:
        _tb = traceback.extract_tb(sys.exc_info()[2])
        _line = None
        for frame in reversed(_tb):
            if frame.filename == '<user>':
                _line = frame.lineno
                break
        _result["error"] = {"type": type(e).__name__, "msg": str(e), "line": _line}

    sys.stdout = _original_stdout
    _result["stdout"] = _stdout_capture.getvalue()

_result
`
}

function getHint(errType: string, errMsg: string): string {
  const msg = errMsg.toLowerCase()
  if (msg.includes('unexpected indent')) return 'Remove extra spaces at the start of this line.'
  if (msg.includes('expected an indented block')) return 'Add indented code after if/for/def/while statement.'
  if (msg.includes('invalid syntax')) return 'Check for missing colons, brackets, or quotes.'
  if (msg.includes('unindent does not match')) return 'Fix indentation - use consistent 4 spaces.'
  if (msg.includes('unterminated string')) return 'Close your string with matching quote.'
  if (msg.includes("'nonetype'") || msg.includes('nonetype')) return 'A variable is None. Check function returns a value.'
  if (msg.includes('not defined')) return 'Variable or function not defined. Check spelling.'
  if (msg.includes('not subscriptable')) return 'Cannot use [] on this type. Check variable type.'
  if (msg.includes('unsupported operand')) return 'Cannot perform this operation between these types.'
  if (msg.includes('takes') && msg.includes('argument')) return 'Wrong number of arguments passed to function.'
  if (msg.includes('object is not callable')) return 'Trying to call something that is not a function.'
  if (msg.includes('index out of range')) return 'List index is too large. Check list length.'
  if (msg.includes('division by zero')) return 'Cannot divide by zero. Add a check before division.'

  const hints: Record<string, string> = {
    SyntaxError: 'Check syntax: missing colons, brackets, or quotes.',
    IndentationError: 'Use consistent 4-space indentation.',
    NameError: 'Variable or function not defined. Check spelling.',
    TypeError: 'Operation on incompatible types. Check your data types.',
    KeyError: 'Dictionary key not found. Use .get() method.',
    ValueError: 'Invalid value provided. Check your data.',
    ZeroDivisionError: 'Cannot divide by zero.',
    IndexError: 'List index out of range. Check list length.',
    AttributeError: 'Object does not have this attribute or method.',
  }
  return hints[errType] || 'Check the error message and review your code.'
}

async function handleRun() {
  output.value = null
  clearMarkers()

  const inputObj = parseInput()
  if (!inputObj) return

  isExecuting.value = true
  hasRun.value = true
  const maxLine = userCodeLineCount.value

  try {
    pyodide!.globals.set('__input_data', inputObj)
    const raw = await pyodide!.runPythonAsync(buildExecutionCode(code.value))
    const res = toJS(raw) as { output?: unknown; stdout?: string; error?: { type: string; msg: string; line: number | null } | null }

    if (res.error) {
      const { type, msg, line } = res.error
      const validLine = (line && line >= 1 && line <= maxLine) ? line : null
      output.value = { console: res.stdout, error: { msg: `${type}: ${msg}`, line: validLine, hint: getHint(type, msg) } }
      if (validLine) setMarker(validLine, `${type}: ${msg}`)
    } else {
      output.value = { result: res.output, console: res.stdout }
    }
  } catch (err) {
    const rawMsg = err instanceof Error ? err.message : String(err)
    output.value = { error: { msg: rawMsg, line: null, hint: 'An unexpected error occurred.' } }
  } finally {
    isExecuting.value = false
    try { pyodide?.globals.delete('__input_data') } catch {}
  }
}

function parseInput(): Record<string, unknown> | null {
  const raw = inputData.value.trim()
  if (!raw) { UIkit.modal.alert('Input data is missing.<br><br>Example: {"channel_1": 1}'); return null }
  try {
    const p = JSON.parse(raw)
    if (typeof p !== 'object' || p === null || Array.isArray(p)) { UIkit.modal.alert('Input must be a JSON object.'); return null }
    return p
  } catch (e) { UIkit.modal.alert(`Invalid JSON: ${e instanceof Error ? e.message : e}`); return null }
}

function handleDebug() {
  if (!hasRun.value) { UIkit.notification({ message: 'Run the code first', status: 'warning', pos: 'top-center' }); return }
  if (output.value?.error) {
    const { msg, line, hint } = output.value.error
    if (line) setMarker(line, msg)
    UIkit.modal.alert(`<strong>${line ? `Line ${line}: ` : ''}${msg}</strong><br><br>💡 ${hint}`)
  } else {
    UIkit.notification({ message: '✅ No errors found', status: 'success', pos: 'top-center' })
  }
}

function setMarker(line: number, msg: string) {
  const ed = editorRef.value?.editor as { getModel: () => { getLineCount: () => number; getLineLength: (n: number) => number } | null; revealLineInCenter: (n: number) => void } | undefined
  if (!ed || !monaco) return
  const model = ed.getModel()
  if (!model) return
  const ln = Math.min(Math.max(1, line), model.getLineCount())
  monaco.editor.setModelMarkers(model, 'err', [{ startLineNumber: ln, startColumn: 1, endLineNumber: ln, endColumn: model.getLineLength(ln) + 1, message: msg, severity: monaco.MarkerSeverity.Error }])
  ed.revealLineInCenter(ln)
}

function clearMarkers() {
  const ed = editorRef.value?.editor as { getModel: () => unknown } | undefined
  if (ed?.getModel() && monaco) monaco.editor.setModelMarkers(ed.getModel(), 'err', [])
}

function handleCancel() {
  code.value = originalCode.value
  emit('close')
}

function handleSave() {
  UIkit.modal.confirm('Save changes to this transformation?').then(
    () => { emit('save', code.value); emit('close') },
    () => { code.value = originalCode.value; emit('close') }
  )
}

function formatOutput(v: unknown, indent = 2): string {
  if (v == null) return String(v)
  try { return typeof v === 'object' ? JSON.stringify(v, null, indent) : String(v) } catch { return String(v) }
}

const outputType = computed<'table' | 'json' | 'text' | 'none'>(() => {
  const r = output.value?.result
  if (r === null || r === undefined) return 'none'
  if (Array.isArray(r) && r.length > 0 && typeof r[0] === 'object' && r[0] !== null && !Array.isArray(r[0])) return 'table'
  if (typeof r === 'object') return 'json'
  return 'text'
})

const tableCols = computed(() => {
  if (outputType.value !== 'table') return []
  const first = (output.value?.result as Record<string, unknown>[])?.[0]
  return first ? Object.keys(first) : []
})

const tableRows = computed(() => outputType.value === 'table' ? output.value?.result as Record<string, unknown>[] : [])
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="te-overlay" :class="{ dark: isDark }" @click.self="handleCancel">
      <div class="te-modal" :class="{ dark: isDark }">
        <div class="te-header">
          <h2 class="te-title">{{ nodeName }}</h2>
          <span class="te-status" :class="{ loading: pyodideLoading, ready: pyodideReady && !pyodideLoading }">
            {{ pyodideLoading ? '⏳ Loading...' : pyodideReady ? '✅ Ready' : '❌ Error' }}
          </span>
        </div>

        <div class="te-content">
          <div class="te-input">
            <label>Input Data (JSON):</label>
            <textarea v-model="inputData" placeholder='{"channel_1": 1, "channel_2": 2}' :disabled="isExecuting" />
          </div>

          <div class="te-editor">
            <CodeEditor
              ref="editorRef"
              v-model:value="code"
              language="python"
              :theme="isDark ? 'vs-dark' : 'vs-light'"
              :options="editorOptions"
            />
          </div>

          <div v-if="hasRun" class="te-output">
            <label>Output:</label>
            <div class="te-output-content" :class="{ dark: isDark }">
              <template v-if="!output?.error">
                <pre v-if="output?.console" class="console">{{ output.console }}</pre>
                <template v-if="output?.result !== null && output?.result !== undefined">
                  <table v-if="outputType === 'table'" class="te-table">
                    <thead><tr><th v-for="c in tableCols" :key="c">{{ c }}</th></tr></thead>
                    <tbody><tr v-for="(row, i) in tableRows" :key="i"><td v-for="c in tableCols" :key="c">{{ formatOutput(row[c], 0) }}</td></tr></tbody>
                  </table>
                  <pre v-else-if="outputType === 'json'" class="json">{{ formatOutput(output.result) }}</pre>
                  <pre v-else class="text">{{ output.result }}</pre>
                </template>
                <div v-else-if="!output?.console" class="empty">(No output returned)</div>
              </template>
              <div v-else class="error">
                <div class="error-line" v-if="output.error.line">📍 Line {{ output.error.line }}</div>
                <div class="error-hint">💡 {{ output.error.hint }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="te-footer">
          <button class="te-btn te-btn-cancel" @click="handleCancel">Cancel</button>
          <div class="te-footer-right">
            <button class="te-btn te-btn-run" :disabled="!canRun" @click="handleRun">
              {{ isExecuting ? '⏳ Running...' : '▶ Run Transformation' }}
            </button>
            <button class="te-btn te-btn-debug" :disabled="isExecuting" @click="handleDebug">🔍 Debug</button>
            <button class="te-btn te-btn-save" @click="handleSave">Save</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
