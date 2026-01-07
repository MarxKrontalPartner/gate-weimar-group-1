<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref, watch, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import UIkit from 'uikit'
import { loadPyodide, type PyodideInterface } from 'pyodide'

declare const monaco:
  | {
      editor: { setModelMarkers: (m: unknown, o: string, markers: unknown[]) => void }
      MarkerSeverity: { Error: number }
    }
  | undefined

const { updateNodeData } = useVueFlow()
const showModal = ref(false)
let lastSavedCode = ''
const props = defineProps(['id', 'data', 'isDark'])

//props specifically for light/dark mode

const reactiveData = reactive(props.data)

const editorRef = ref<{ editor: unknown } | null>(null)

let pyodide: PyodideInterface | null = null
let pyodidePromise: Promise<PyodideInterface> | null = null

const inputData = ref('')
const isExecuting = ref(false)
const pyodideReady = ref(false)
const pyodideLoading = ref(false)

const output = ref<{
  result?: unknown
  stdout?: string
  error?: { type: string; msg: string; line: number | null; hint: string }
} | null>(null)

const tableColumns = computed(() => {
  if (!output.value?.result || !Array.isArray(output.value.result)) return []

  const rows = output.value.result as Record<string, unknown>[]
  return [...new Set(rows.flatMap((r) => Object.keys(r)))]
})

const onModalToggle = () => {
  if (!showModal.value) {
    lastSavedCode = reactiveData.code
    inputData.value = ''
    output.value = null
    clearMarkers()
    if (!pyodideReady.value && !pyodideLoading.value) initPyodide()
  }
  showModal.value = !showModal.value
}

const onSave = () => {
  updateNodeData(props.id, {
    code: reactiveData.code,
  })
  onModalToggle()
}

const onCancel = () => {
  reactiveData.code = lastSavedCode
  onModalToggle()
}

const editorOptions = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
}

const clearMarkers = () => {
  const ed = editorRef.value?.editor as { getModel?: () => unknown } | undefined
  const model = ed?.getModel?.()
  if (!model || !monaco) return
  monaco.editor.setModelMarkers(model, 'python-errors', [])
}

const setMarkers = (lines: number[], message: string) => {
  const ed = editorRef.value?.editor as
    | { getModel?: () => unknown; revealLineInCenter?: (n: number) => void }
    | undefined

  const modelUnknown = ed?.getModel?.()
  if (!modelUnknown || !monaco) return

  const model = modelUnknown as {
    getLineCount: () => number
    getLineLength: (n: number) => number
  }

  const maxLine = model.getLineCount()
  const uniqueLines = [...new Set(lines)]
    .filter(Number.isInteger)
    .map((l) => Math.min(Math.max(1, l), maxLine))
    .sort((a, b) => a - b)

  const markers = uniqueLines.map((ln) => ({
    startLineNumber: ln,
    startColumn: 1,
    endLineNumber: ln,
    endColumn: model.getLineLength(ln) + 1,
    message,
    severity: monaco.MarkerSeverity.Error,
  }))

  monaco.editor.setModelMarkers(modelUnknown, 'python-errors', markers)

  const firstLine = uniqueLines[0]
  if (firstLine !== undefined) ed?.revealLineInCenter?.(firstLine)
}

// lazy-load pyodide once
const initPyodide = async () => {
  if (pyodide) {
    pyodideReady.value = true
    pyodideLoading.value = false
    return
  }

  pyodideLoading.value = true

  try {
    if (!pyodidePromise) {
      pyodidePromise = loadPyodide({
        indexURL: `${import.meta.env.BASE_URL}pyodide/`,
      })
    }

    pyodide = await pyodidePromise
    pyodideReady.value = true
  } catch {
    pyodideReady.value = false
    UIkit.notification({ message: 'Failed to load Python runtime (Pyodide).', status: 'danger' })
  } finally {
    pyodideLoading.value = false
  }
}

const parseInput = (): Record<string, unknown> | null => {
  const raw = inputData.value.trim()

  if (!raw) {
    UIkit.modal.alert('Input data is missing.<br><br>Example: {"channel_1": 1}')
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      UIkit.modal.alert('Input must be a JSON object.')
      return null
    }
    return parsed
  } catch (e) {
    UIkit.modal.alert(`Invalid JSON: ${e instanceof Error ? e.message : e}`)
    return null
  }
}

// safe string escape for embedding into python triple quotes
const escapeForPython = (str: string): string =>
  str.replace(/\\/g, '\\\\').replace(/'''/g, "\\'\\'\\'")

const buildExecutionCode = (userCode: string): string => {
  const escaped = escapeForPython(userCode)

  return `
import sys, traceback, ast
from io import StringIO

_user_code = '''${escaped}'''
_result = {"output": None, "stdout": "", "error": None}

_stdout = StringIO()
_original_stdout = sys.stdout

class Logger:
    def info(self, m): print(f"INFO: {m}")
    def warning(self, m): print(f"WARN: {m}")
    def error(self, m): print(f"ERROR: {m}")
    def debug(self, m): print(f"DEBUG: {m}")

def _to_json(o, depth=0):
    if depth > 10:
        return str(o)

    try:
        if hasattr(o, "to_py"):
            o = o.to_py()
    except Exception:
        return str(o)

    if isinstance(o, dict):
        return {str(k): _to_json(v, depth + 1) for k, v in o.items()}

    if isinstance(o, (list, tuple)):
        return [_to_json(v, depth + 1) for v in o]

    if isinstance(o, (str, int, float, bool)) or o is None:
        return o

    return str(o)

try:
    ast.parse(_user_code)
except SyntaxError as e:
    _result["error"] = {
        "type": "SyntaxError",
        "msg": e.msg or str(e),
        "line": e.lineno,
        "lines": [e.lineno] if e.lineno else []
    }
else:
    sys.stdout = _stdout
    try:
        import json
        env = {"__builtins__": __builtins__, "logger": Logger(), "_input": json.loads(__input_data)}
        if "while True" in _user_code or "while 1" in _user_code:
            raise RuntimeError("Infinite loop detected: please add a break condition.")
        exec(compile(_user_code, "<user>", "exec"), env)


        funcs = [(n, v) for n, v in env.items() if callable(v) and not n.startswith("_") and n != "logger"]

        target_name, target_fn = max(
            funcs,
            key=lambda x: (x[0].lower() == "transform", "transform" in x[0].lower(), x[0].lower() in {"main", "process", "run", "execute"}),
            default=(None, None),
        )

        if target_fn:
            inp = env.get("_input")
            try:
                _result["output"] = _to_json(target_fn(inp))
            except TypeError:
                _result["output"] = _to_json(target_fn(**{next(iter(target_fn.__code__.co_varnames), "row"): inp}))



    except Exception as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lines = [f.lineno for f in tb if f.filename == "<user>" and f.lineno is not None]
        _result["error"] = {
            "type": type(e).__name__,
            "msg": str(e),
            "line": lines[-1] if lines else None,
            "lines": lines,
        }
    finally:
        sys.stdout = _original_stdout
        _result["stdout"] = _stdout.getvalue()

_result
`
}

// minimal and useful hints only
const getHint = (type: string, msg: string): string => {
  const m = msg.toLowerCase()
  if (type === 'SyntaxError') return 'Check syntax: missing colons, brackets, or quotes.'
  if (type === 'IndentationError') return 'Fix indentation. Use consistent 4 spaces.'
  if (m.includes('not defined')) return 'Name not defined. Check spelling or define the variable.'
  return 'Review the error message and your code.'
}

const withTimeout = <T,>(p: Promise<T>, ms = 8000): Promise<T> =>
  Promise.race([
    p,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error('Execution timed out')), ms)),
  ])

const onRunTransformation = async () => {
  output.value = null
  clearMarkers()

  const inputObj = parseInput()
  if (!inputObj) return

  if (!pyodide) {
    await initPyodide()
    if (!pyodide) return
  }

  isExecuting.value = true

  try {
    pyodide.globals.set('__input_data', JSON.stringify(inputObj))

    const raw = await withTimeout(
      pyodide.runPythonAsync(buildExecutionCode(reactiveData.code)),
      8000,
    )

    let res: unknown = raw

    if (raw && typeof raw === 'object' && 'toJs' in raw && 'destroy' in raw) {
      const proxy = raw as {
        toJs: (opts?: { dict_converter?: (e: Iterable<[string, unknown]>) => unknown }) => unknown
        destroy: () => void
      }
      res = proxy.toJs({ dict_converter: Object.fromEntries })
      proxy.destroy()
    }

    const result = res as {
      output?: unknown
      stdout?: string
      error?: { type: string; msg: string; line: number | null; lines?: number[] } | null
    }

    if (result.error) {
      const lines = (result.error.lines ?? []).filter((n) => Number.isInteger(n))

      output.value = {
        stdout: result.stdout,
        error: {
          type: result.error.type,
          msg: result.error.msg,
          line: result.error.line ?? null,
          hint: getHint(result.error.type, result.error.msg),
        },
      }

      if (lines.length > 0) {
        setMarkers(lines, `${result.error.type}: ${result.error.msg}`)
      } else if (result.error.line) {
        setMarkers([result.error.line], `${result.error.type}: ${result.error.msg}`)
      }
    } else {
      output.value = { result: result.output, stdout: result.stdout }
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    output.value = {
      error: {
        type: 'RuntimeError',
        msg,
        line: null,
        hint: 'An unexpected runtime error occurred.',
      },
    }
  } finally {
    isExecuting.value = false
    try {
      pyodide.globals.delete('__input_data')
    } catch {}
  }
}

watch(
  () => props.data,
  (newData) => {
    Object.assign(reactiveData, newData)
  },
  { deep: true },
)
</script>

<template>
  <div class="container dark">
    <Handle type="target" :position="Position.Left" :connectable="1" />
    <input
      type="text"
      v-model="reactiveData.content"
      class="nodrag uk-input input-nodes"
      name="transformation-name"
    />

    <!-- This is a button toggling the modal -->
    <button
      @click="onModalToggle"
      class="uk-button uk-button-primary uk-button-small"
      uk-toggle="target: #modal-example"
      type="button"
    >
      {{ $t('btns.editCode') }}
    </button>

    <!-- This is the modal -->
    <div id="modal-example" uk-modal="esc-close: false; bg-close: false" v-if="showModal">
      <div class="uk-modal-dialog uk-modal-body">
        <h2 class="uk-modal-title">{{ reactiveData.content }}</h2>

        <div class="uk-margin-small">
          <label class="uk-form-label">Input Data (JSON):</label>

          <textarea
            v-model="inputData"
            class="uk-textarea nodrag te-textarea"
            rows="3"
            placeholder='{"channel_1": 1, "channel_2": 2}'
            :disabled="isExecuting"
          />

          <div class="uk-margin-small-top">
            <span v-if="pyodideLoading" class="uk-text-muted">
              <span uk-spinner="ratio: 0.5" class="uk-margin-small-right"></span>
              {{ $t('status.loadingRuntime') }}
            </span>

            <span v-else-if="pyodideReady" class="uk-text-success">
              {{ $t('status.runtimeReady') }}
            </span>

            <span v-else class="uk-text-danger">
              {{ $t('status.runtimeUnavailable') }}
            </span>
          </div>
        </div>

        <div class="code-editor-container">
          <CodeEditor
            ref="editorRef"
            v-model:value="reactiveData.code"
            language="python"
            :theme="isDark ? 'vs-dark' : 'vs-light'"
            :options="editorOptions"
          />
        </div>

        <div v-if="output" class="uk-margin-small">
          <h4 class="uk-heading-bullet uk-margin-small-bottom">
            {{ $t('labels.output') }}
          </h4>

          <div v-if="output.error" class="uk-alert-danger" uk-alert>
            <p>
              <strong>{{ output.error.type }}:</strong>
              {{ output.error.msg }}
            </p>

            <p v-if="output.error.line">
              <strong>{{ $t('labels.line') }}:</strong>
              {{ output.error.line }}
            </p>

            <p>
              <strong>{{ $t('labels.hint') }}:</strong>
              {{ output.error.hint }}
            </p>

            <pre
              v-if="output.stdout"
              class="uk-padding-small uk-margin-small-top uk-background-muted te-output-block"
              >{{ output.stdout }}</pre
            >
          </div>

          <div v-else>
            <pre
              v-if="output.stdout"
              class="uk-padding-small uk-margin-small-bottom uk-background-muted te-output-block"
              >{{ output.stdout }}</pre
            >

            <div class="te-output-scroll">
              <table
                v-if="
                  Array.isArray(output.result) &&
                  output.result.length > 0 &&
                  typeof output.result[0] === 'object' &&
                  output.result[0] !== null &&
                  !Array.isArray(output.result[0])
                "
                class="uk-table uk-table-divider uk-table-small uk-table-hover uk-margin-remove"
                :class="{ 'te-output-block': true }"
              >
                <thead>
                  <tr>
                    <th v-for="col in tableColumns" :key="col">
                      {{ col }}
                    </th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-for="(row, i) in output.result" :key="i">
                    <td v-for="col in tableColumns" :key="col">
                      {{
                        typeof row[col] === 'object' && row[col] !== null
                          ? JSON.stringify(row[col])
                          : row[col]
                      }}
                    </td>
                  </tr>
                </tbody>
              </table>

              <pre
                v-else
                class="uk-padding-small uk-background-muted te-output-block uk-margin-remove"
                >{{
                  typeof output.result === 'object'
                    ? JSON.stringify(output.result, null, 2)
                    : output.result
                }}</pre
              >
            </div>
          </div>
        </div>

        <p class="uk-text-right button-container">
          <button
            @click="onCancel"
            class="uk-button uk-modal-close uk-cancel-button uk-button-small"
            type="button"
          >
            {{ $t('btns.cancel') }}
          </button>

          <button
            @click="onRunTransformation"
            class="uk-button uk-button-primary uk-button-small"
            type="button"
            :disabled="isExecuting || !reactiveData.code?.trim() || !pyodideReady"
          >
            <span v-if="isExecuting" uk-spinner="ratio: 0.6" class="uk-margin-small-right"></span>
            {{ isExecuting ? $t('btns.running') : $t('btns.runTransformation') }}
          </button>

          <button
            @click="onSave"
            class="uk-button uk-modal-close uk-button-primary uk-button-small"
            type="button"
          >
            {{ $t('btns.save') }}
          </button>
        </p>
      </div>
    </div>
  </div>

  <Handle type="source" :position="Position.Right" :connectable="1" />
</template>
