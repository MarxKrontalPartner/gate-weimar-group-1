<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref, watch, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import {
  runtimeStatus,
  pyodideWorkerClient as workerClient,
} from '@/utils/customTransformNodeRuntime/pyodideWorkerClient'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const { updateNodeData } = useVueFlow()
const showModal = ref(false)
let lastSavedCode = ''
const props = defineProps(['id', 'data', 'isDark'])

//props specifically for light/dark mode

const reactiveData = reactive(props.data)

const inputData = ref('')

const output = ref<{
  result?: unknown
  stdout?: string
  error?: { type: string; msg: string; line: number | null }
} | null>(null)

const showTestButton = computed(() => {
  return (
    runtimeStatus.value === 'idle' ||
    runtimeStatus.value === 'loading' ||
    runtimeStatus.value === 'error'
  )
})

const showAbortButton = computed(() => runtimeStatus.value === 'executing')

const onModalToggle = () => {
  if (!showModal.value) {
    lastSavedCode = reactiveData.code
    inputData.value = ''
    output.value = null
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

const parseInput = (): Record<string, unknown> | null => {
  const raw = inputData.value.trim()

  if (!raw) {
    alert(`${t('text.transformNodeAlert.missingInputData')}{"channel_1": 1, "channel_2": 2}`)
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      alert(t('text.transformNodeAlert.jsonInputRequired'))
      return null
    }
    return parsed
  } catch (e) {
    alert(t('text.transformNodeAlert.invalidJson') + `${e instanceof Error ? e.message : e}`)
    return null
  }
}

const onTestRuntime = async () => {
  if (runtimeStatus.value === 'ready' || runtimeStatus.value === 'loading') return

  try {
    await workerClient.init()
  } catch {
    alert(t('text.transformNodeAlert.workerInitializationError'))
  }
}

const onAbort = () => {
  workerClient.terminate()
  alert(t('text.transformNodeAlert.messageOnAbort'))
}

const onRunTransformation = async () => {
  const inputObj = parseInput()
  if (!inputObj) return

  output.value = null

  try {
    const result = await workerClient.run(reactiveData.code, inputObj, 8000)

    output.value = result.error
      ? {
          stdout: result.stdout,
          error: {
            type: result.error.type,
            msg: result.error.msg,
            line: result.error.line ?? null,
          },
        }
      : { result: result.output, stdout: result.stdout }
  } catch (err) {
    if (runtimeStatus.value === 'idle') {
      alert(t('text.transformNodeAlert.workerTimedOut'))
    } else {
      alert(err instanceof Error ? err.message : String(err))
    }
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
          <div v-if="!showTestButton" class="uk-margin-small-top">
            <h4 class="uk-margin-small-bottom">{{ $t('labels.enterJsonInput') }}</h4>

            <textarea
              v-model="inputData"
              class="uk-textarea nodrag te-ip-op-block"
              rows="3"
              placeholder='{"channel_1": 1, "channel_2": 2}'
              :disabled="runtimeStatus === 'executing'"
            />
          </div>

          <div class="uk-margin-small">
            <span v-if="runtimeStatus === 'loading'" class="uk-text-muted">
              <span uk-spinner="ratio: 0.5" class="uk-margin-small-right"></span>
              {{ $t('status.loadingRuntime') }}
            </span>

            <span
              v-else-if="runtimeStatus === 'ready' || runtimeStatus === 'executing'"
              class="uk-text-success"
            >
              {{ $t('status.runtimeReady') }}
            </span>

            <span v-else-if="runtimeStatus === 'error'" class="uk-text-danger">
              {{ $t('status.runtimeError') }}
            </span>

            <span v-else class="uk-text-muted">
              {{ $t('status.runtimeUnavailable') }}
            </span>
          </div>
        </div>

        <div class="code-editor-container">
          <CodeEditor
            v-model:value="reactiveData.code"
            language="python"
            :theme="isDark ? 'vs-dark' : 'vs-light'"
            :options="editorOptions"
          />
        </div>

        <div v-if="output" class="uk-margin-small">
          <h4 class="uk-margin-small-bottom">
            {{ $t('labels.output') }}
          </h4>

          <div
            v-if="output.error"
            class="uk-padding-small uk-margin-small-top te-ip-op-block uk-text-danger"
          >
            <p>
              <strong>{{ output.error.type }}:</strong>
              {{ output.error.msg }}
            </p>

            <p v-if="output.error.line">
              <strong>{{ $t('labels.line') }}:</strong>
              {{ output.error.line }}
            </p>

            <pre
              v-if="output.stdout"
              class="uk-padding-small uk-margin-small-top uk-background-muted te-ip-op-block"
              v-text="output.stdout"
            ></pre>
          </div>

          <div v-else class="te-output-scroll">
            <pre
              class="uk-padding-small uk-margin-small-top uk-background-muted te-ip-op-block"
              v-text="JSON.stringify(output.result, null, 2)"
            ></pre>
            <pre
              v-if="output.stdout"
              class="uk-padding-small uk-margin-small-top uk-background-muted te-ip-op-block"
              v-text="output.stdout"
            ></pre>
          </div>
        </div>

        <div
          class="uk-padding-small uk-margin-small uk-flex uk-flex-between uk-flex-middle button-container"
        >
          <div>
            <button
              v-if="showAbortButton"
              @click="onAbort()"
              class="uk-button uk-delete-button uk-button-small"
            >
              {{ $t('btns.abort') }}
            </button>

            <button
              v-else-if="showTestButton"
              @click="onTestRuntime"
              class="uk-button uk-button-primary uk-button-small"
              type="button"
              :disabled="runtimeStatus === 'loading'"
            >
              <span
                v-if="runtimeStatus === 'loading'"
                uk-spinner="ratio: 0.6"
                class="uk-margin-small-right"
              />
              {{ $t('btns.testRuntime') }}
            </button>
          </div>

          <div>
            <button
              @click="onCancel"
              class="uk-button uk-modal-close uk-cancel-button uk-button-small"
              type="button"
            >
              {{ $t('btns.cancel') }}
            </button>

            <button
              v-if="!showTestButton"
              @click="onRunTransformation"
              class="uk-button uk-button-primary uk-button-small"
              type="button"
              :disabled="runtimeStatus === 'executing'"
            >
              <span
                v-if="runtimeStatus === 'executing'"
                uk-spinner="ratio: 0.6"
                class="uk-margin-small-right"
              />
              {{
                runtimeStatus === 'executing' ? $t('btns.running') : $t('btns.runTransformation')
              }}
            </button>

            <button
              @click="onSave"
              class="uk-button uk-modal-close uk-button-primary uk-button-small"
              type="button"
            >
              {{ $t('btns.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <Handle type="source" :position="Position.Right" :connectable="1" />
</template>
