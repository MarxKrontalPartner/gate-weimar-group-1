<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted, reactive, nextTick, inject, type Ref } from 'vue'
import {
  ConnectionMode,
  VueFlow,
  useVueFlow,
  Panel,
  type Edge,
  type FlowExportObject,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { initialEdges, initialNodes } from '@/assets/initial-flow.ts'
import CustomTransformNode from '@/components/CustomTransformNode.vue'
import CustomInputNode from '@/components/CustomInputNode.vue'
import CustomOutputNode from '@/components/CustomOutputNode.vue'
import UIkit from 'uikit'
import CustomIntermediateNode from '@/components/CustomIntermediateNode.vue'
import { type Payload } from '@/assets/payload.ts'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
/**
 * `useVueFlow` provides:
 * 1. a set of methods to interact with the VueFlow instance (like `fitView`, `setViewport`, `addEdges`, etc)
 * 2. a set of event-hooks to listen to VueFlow events (like `onInit`, `onNodeDragStop`, `onConnect`, etc)
 * 3. the internal state of the VueFlow instance (like `nodes`, `edges`, `viewport`, etc)
 */
const {
  onInit,
  onConnect,
  addEdges,
  toObject,
  fromObject,
  removeEdges,
  removeNodes,
  getOutgoers,
  getSelectedNodes,
  setViewport,
} = useVueFlow()

const nodes = ref(initialNodes)

const edges = ref(initialEdges)

const inputMessages = ref<unknown[]>([])
const outputMessages = ref<unknown[]>([])
const inputTopicName = ref<string>('')
const outputTopicName = ref<string>('')
const showIoPanel = ref(false)
const lastRunCompleted = ref(false)

type PipelineStatus = 'running' | 'completed' | 'failed'

interface PipelineState {
  id: string
  status: PipelineStatus
  message: string
}

const currentPipeline = ref<PipelineState | null>(null)

let statusTimer: number | null = null

const isRunning = ref(false)

const runForm = reactive({
  allowProducer: false,
  n_channels: 10,
  frequency: 1,
  runtime: 120,
})

let ws: WebSocket | null = null

const dark = inject('isDark') as Ref<boolean>

onInit((vueFlowInstance) => {
  // instance is the same as the return of `useVueFlow`
  vueFlowInstance.fitView()
  addToHistory()
})

/**
 * onConnect is called when a new connection is created.
 *
 * You can add additional properties to your new edge (like a type or label) or block the creation altogether by not calling `addEdges`
 */
onConnect((connection) => {
  addEdges(connection)
})

watch(
  dark,
  (newDarkValue) => {
    if (newDarkValue) {
      document.body.classList.add('dark-mode')
    } else {
      document.body.classList.remove('dark-mode')
    }
  },
  { immediate: true },
)

function removeEdge({ edge }: { edge: Edge }) {
  removeEdges(edge.id)
}

function delConfirm() {
  UIkit.modal('#del-confirm').show()
}

let transformationNodeNumber = 2

function addNode() {
  const id = Date.now().toString()
  transformationNodeNumber += 1

  nodes.value.push({
    id,
    position: { x: 400, y: 500 },
    type: 'custom-transform',
    data: {
      content: `Transform ${transformationNodeNumber}`,
      code: `def transform${transformationNodeNumber}(row: dict) -> dict:
    logger.info(f"before :: row :: {row}")
    for key in row:
        if key.startswith("channel_"):
            row[key] += 10
    logger.info(f"after :: row :: {row}")
    return row
  `,
    },
  })
}

function addIntermediateNode() {
  const id = Date.now().toString()

  nodes.value.push({
    id,
    position: { x: 400, y: 500 },
    type: 'custom-intermediate',
    data: { content: 'Intermediate Topic' },
  })
}

const validateRunForm = () => {
  if (runForm.runtime == null || runForm.runtime < 5 || !Number.isInteger(runForm.runtime)) {
    alert(t('text.validation.runtimeError'))
    return false
  }
  if (runForm.allowProducer) {
    if (
      runForm.n_channels == null ||
      runForm.n_channels <= 0 ||
      !Number.isInteger(runForm.n_channels)
    ) {
      alert(t('text.validation.channelsError'))
      return false
    }
    if (runForm.frequency == null || runForm.frequency <= 0) {
      alert(t('text.validation.frequencyError'))
      return false
    }
  }
  return true
}

const connectWebSocket = (): Promise<boolean> => {
  if (ws) return Promise.resolve(true)

  return new Promise((resolve) => {
    ws = new WebSocket('/ws/stream')

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      const { pipeline_id, category, type, data, topic } = msg

      if (!category || !type) {
        console.warn('Missing category or type in WebSocket message', msg)
        return
      }

      switch (category) {
        case 'lifecycle':
          handleLifecycleEvent(type, data, pipeline_id)
          break

        case 'stream':
          handleStreamEvent(data, pipeline_id, topic)
          break

        default:
          console.warn('Unknown event category:', category)
      }
    }

    ws.onopen = () => {
      console.log('WebSocket connected')
      resolve(true)
    }

    ws.onerror = () => {
      console.warn('WebSocket error')
      ws = null
      resolve(false)
    }

    ws.onclose = () => {
      console.warn('WebSocket closed')
      ws = null
      resolve(false)
    }

    setTimeout(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        ws = null
        resolve(false)
      }
    }, 4000)
  })
}

// --------------------
// Handlers
// --------------------
const handleLifecycleEvent = (type: string, data: unknown, pipeline_id: string) => {
  if (!currentPipeline.value || currentPipeline.value.id !== pipeline_id) {
    // ignore messages for non-running pipeline
    return
  }

  switch (type) {
    case 'segment_started':
      currentPipeline.value.status = 'running'
      currentPipeline.value.message = 'Segment started'
      break

    case 'segment_completed':
      currentPipeline.value.status = 'running'
      currentPipeline.value.message = 'Segment completed'
      break

    case 'completed':
      currentPipeline.value.status = 'completed'
      currentPipeline.value.message = 'Pipeline completed'
      isRunning.value = false
      lastRunCompleted.value = true
      break

    case 'failed':
      currentPipeline.value.status = 'failed'
      if (typeof data === 'string') {
        currentPipeline.value.message = data
      } else {
        currentPipeline.value.message = 'Pipeline failed'
      }
      isRunning.value = false
      break
  }

  // Clear any previous timer
  if (statusTimer) {
    clearTimeout(statusTimer)
    statusTimer = null
  }

  // Hide ONLY when completed or failed (after 5s)
  if (currentPipeline.value.status === 'completed' || currentPipeline.value.status === 'failed') {
    statusTimer = window.setTimeout(() => {
      currentPipeline.value = null
    }, 5000)
  }

  console.log(`[Pipeline ${pipeline_id}]`, currentPipeline.value.message)
}

function pushLatest(arr: unknown[], item: unknown) {
  arr.push(item)
  if (arr.length > 5) arr.shift() // Keep only the latest 5 messages
}

const handleStreamEvent = (data: unknown, pipeline_id: string, topic?: string) => {
  if (!currentPipeline.value || currentPipeline.value.id !== pipeline_id || !topic) {
    return
  }

  if (topic === inputTopicName.value) {
    pushLatest(inputMessages.value, data)
  } else if (topic === outputTopicName.value) {
    pushLatest(outputMessages.value, data)
  }
}

const closeWebSocket = () => {
  if (ws) {
    ws.close()
    ws = null
  }
}

const createRequest = async () => {
  if (!validateRunForm()) return
  UIkit.modal('#run-pipeline-modal')?.hide()

  const obj = toObject()
  let transformations: string[] = []
  const payload: Payload[] = []

  const inputNode = obj.nodes.find((n) => n.type === 'custom-input')
  const outputNode = obj.nodes.find((n) => n.type === 'custom-output')

  if (!inputNode || !outputNode) {
    alert(t('text.missingIO'))
    return
  }

  // -----------------------------
  // Generate unique pipeline ID
  // -----------------------------
  const pipelineId = crypto.randomUUID()

  const tempPayload: Payload = {
    pipeline_id: pipelineId,
    input_topic: inputNode.data.content,
    output_topic: outputNode.data.content,
    transformations: [],
    allow_producer: false,
    n_channels: runForm.n_channels,
    frequency: runForm.frequency,
    runtime: runForm.runtime,
  }

  let node = inputNode

  while (true) {
    const connectedNode = getOutgoers(node)[0]

    if (connectedNode && connectedNode.id !== outputNode?.id) {
      if (connectedNode.type == 'custom-intermediate') {
        //separate the requests
        tempPayload.transformations = transformations
        tempPayload.output_topic = connectedNode.data.content
        payload.push({ ...tempPayload })

        tempPayload.input_topic = connectedNode.data.content
        tempPayload.output_topic = outputNode.data.content
        transformations = []
      } else {
        transformations.push(connectedNode.data.code)
      }

      node = connectedNode
    } else {
      // check if the last node is the output node ie if the graph is connected
      if (!connectedNode || connectedNode.id !== outputNode?.id) {
        alert(t('text.graphNotConnected'))
        return
      }
      tempPayload.transformations = transformations
      payload.push({ ...tempPayload })
      break
    }
  }

  if (payload?.[0] && runForm.allowProducer) {
    payload[0].allow_producer = runForm.allowProducer
  }

  console.log('Sending payload:', payload)
  isRunning.value = true

  // Ensure WebSocket connection
  if (!ws && !(await connectWebSocket())) {
    alert(t('text.webSocketError'))
    isRunning.value = false
    return
  }

  // ----------------------------------------
  // POST to FastAPI /start
  // ----------------------------------------
  try {
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', accept: 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      alert(t('text.apiConnectionError'))
      isRunning.value = false
      return
    }

    const result = await res.json()
    console.log('Backend response:', result)

    inputTopicName.value = inputNode.data.content
    outputTopicName.value = outputNode.data.content

    inputMessages.value = []
    outputMessages.value = []
    lastRunCompleted.value = false

    currentPipeline.value = {
      id: pipelineId,
      status: 'running',
      message: 'Pipeline started',
    }
  } catch (err) {
    console.error(err)
    alert(t('text.backendContactError'))
    isRunning.value = false
  }
}

const onExport = () => {
  const blob = new Blob([JSON.stringify(toObject())], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = 'graph.json'
  link.click()

  URL.revokeObjectURL(url)
}

const getFileElement = () => {
  const element = document.getElementById('fileUpload') as HTMLInputElement | null
  if (element) {
    return element
  }
}

const onImport = () => {
  const element = getFileElement()
  if (element) {
    element.click()
  }
}

const uploadJson = (event: Event) => {
  const files = (event.target as HTMLInputElement)?.files
  if (!files || files.length === 0) {
    return
  }

  const file = files[0]

  const reader = new FileReader()

  reader.onload = function (e) {
    try {
      const target = e.target
      if (!target) {
        return
      }
      const jsonText = target.result
      if (typeof jsonText === 'string') {
        const flow = JSON.parse(jsonText)

        if (flow) {
          fromObject(flow)

          const element = getFileElement()
          if (element) {
            element.value = ''
          }
        }
      }
    } catch (error) {
      // Handle malformed JSON content
      console.error('Error parsing JSON', error)
    }
  }

  // readAsText is used for text-based files like JSON, XML, or plain text.
  if (file) {
    reader.readAsText(file)
  }
}

window.addEventListener('keydown', (e) => {
  const isTyping =
    ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName || '') ||
    document.activeElement?.classList.contains('monaco-editor') ||
    document.querySelector('.uk-modal.uk-open')

  if (isTyping) {
    return
  }

  if ((e.key === 'Delete' || e.key === 'Del') && getSelectedNodes.value.length > 0) {
    delConfirm()
  } else if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
    e.preventDefault()
    undo()
  } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
    e.preventDefault()
    redo()
  }
})

const deleteSelectedNodes = () => {
  const selectedNodes = getSelectedNodes.value
  if (selectedNodes.length > 0) {
    removeNodes(selectedNodes, true)
  }
}

const history = ref<FlowExportObject[]>([])
const historyIndex = ref(-1)
const isInternalChange = ref(false)

function debounce(fn: () => void, delay: number) {
  let timeoutId: ReturnType<typeof setTimeout>
  return () => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(), delay)
  }
}

const addToHistory = () => {
  if (isInternalChange.value) return

  const currentState = toObject()

  if (historyIndex.value >= 0) {
    const lastSavedState = history.value[historyIndex.value]
    if (JSON.stringify(currentState) === JSON.stringify(lastSavedState)) {
      return
    }
  }

  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }

  history.value.push(structuredClone(currentState))
  historyIndex.value++

  if (history.value.length > 50) {
    history.value.shift()
    historyIndex.value--
  }
}

watch([nodes, edges], debounce(addToHistory, 500), { deep: true })

const applyState = async (state: FlowExportObject) => {
  nodes.value = state.nodes || []

  await nextTick()

  edges.value = state.edges || []

  if (state.viewport) {
    setViewport(state.viewport)
  }
}

const undo = async () => {
  if (historyIndex.value <= 0 || isInternalChange.value) return

  isInternalChange.value = true

  historyIndex.value--
  const stateToRestore = history.value[historyIndex.value]

  if (stateToRestore) {
    await applyState(stateToRestore)
  }

  setTimeout(() => {
    isInternalChange.value = false
  }, 100)
}

const redo = async () => {
  if (historyIndex.value >= history.value.length - 1 || isInternalChange.value) return

  isInternalChange.value = true

  historyIndex.value++
  const stateToRestore = history.value[historyIndex.value]

  if (stateToRestore) {
    await applyState(stateToRestore)
  }

  setTimeout(() => {
    isInternalChange.value = false
  }, 100)
}

function formatData(data: unknown): string {
  if (typeof data === 'string') return data
  return JSON.stringify(data, null, 2)
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  closeWebSocket()
})
</script>

<template>
  <VueFlow
    v-model="nodes"
    :edges="edges"
    :class="{ dark }"
    class="basic-flow"
    :default-viewport="{ zoom: 1 }"
    :min-zoom="0.2"
    :max-zoom="4"
    @edge-double-click="removeEdge"
    :connection-mode="ConnectionMode.Strict"
    :delete-key-code="null"
    panActivationKeyCode="{ actInsideInputWithModifier: false }"
  >
    <!-- temp fix https://github.com/bcakmakoglu/vue-flow/issues/1999 -->
    <Panel position="bottom-center">
      <div class="panel button-container">
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="addNode">
          {{ $t('btns.addTransformationNode') }}
        </button>
        <button
          class="uk-button uk-button-primary uk-button-small"
          type="button"
          @click="addIntermediateNode"
        >
          {{ $t('btns.addIntermediateNode') }}
        </button>
        <button
          class="uk-button uk-button-primary uk-button-small"
          id="view-results-button"
          type="button"
          uk-toggle="target: #io-modal"
          :disabled="isRunning || !lastRunCompleted"
        >
          {{ $t('btns.viewPipelineResults') }}
        </button>
      </div></Panel
    >
    <Panel position="top-center" style="margin-top: 75px">
      <div class="panel button-container">
        <button
          class="uk-button uk-button-primary uk-button-small"
          type="button"
          uk-toggle="target: #run-pipeline-modal"
          :disabled="isRunning"
        >
          {{ $t('btns.run') }}
        </button>
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="onExport">
          {{ $t('btns.export') }}
        </button>
        <input id="fileUpload" type="file" accept="application/json" @change="uploadJson" hidden />
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="onImport">
          {{ $t('btns.import') }}
        </button>
        <button
          class="uk-button uk-button-small"
          id="delete-button"
          @click="delConfirm"
          :disabled="getSelectedNodes.length === 0"
        >
          {{ $t('btns.deleteConfirm') }}
        </button>
      </div>
    </Panel>

    <template #node-custom-input="props">
      <CustomInputNode :id="props.id" :data="props.data" />
    </template>

    <template #node-custom-output="props">
      <CustomOutputNode :id="props.id" :data="props.data" />
    </template>

    <template #node-custom-transform="props">
      <CustomTransformNode :id="props.id" :data="props.data" :is-dark="dark" />
    </template>

    <template #node-custom-intermediate="props">
      <CustomIntermediateNode :id="props.id" :data="props.data" />
    </template>

    <Background pattern-color="#aaa" :gap="16" />

    <MiniMap node-color="#2b2b32" style="margin-bottom: 55px" />
    <Controls position="bottom-right" style="border: 1px; border-color: black; border-style: solid">
      <span
        title="Undo"
        uk-icon="reply"
        id="additional-control-buttons"
        :style="{ backgroundColor: dark ? '#333333' : 'white' }"
        @click="undo"
      ></span>
      <span
        title="Redo"
        uk-icon="forward"
        id="additional-control-buttons"
        :style="{ backgroundColor: dark ? '#333333' : 'white' }"
        @click="redo"
      ></span>
    </Controls>
  </VueFlow>
  <!-- Input/Output Panel -->
  <div id="io-modal" uk-modal @beforehide="showIoPanel = false">
    <div class="uk-modal-dialog uk-modal-body io-modal-dialog">
      <div class="uk-flex uk-flex-between uk-flex-middle">
        <h2 class="uk-modal-title">
          {{ $t('text.streamInspector') }}
        </h2>

        <button class="uk-modal-close-default" type="button" uk-close></button>
      </div>

      <div class="io-columns-header uk-margin-small-bottom">
        <div class="col input">{{ $t('text.input') }} - {{ inputTopicName }}</div>
        <div class="col output">{{ $t('text.output') }} - {{ outputTopicName }}</div>
      </div>

      <div class="io-scroll">
        <div
          v-for="i in Math.max(inputMessages.length, outputMessages.length)"
          :key="i"
          class="io-columns-body"
        >
          <div class="col input">
            <pre v-if="inputMessages[i - 1]" v-text="formatData(inputMessages[i - 1] as unknown)" />
            <span v-else class="placeholder">—</span>
          </div>

          <div class="col output">
            <pre
              v-if="outputMessages[i - 1]"
              v-text="formatData(outputMessages[i - 1] as unknown)"
            />
            <span v-else class="placeholder">—</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <!-- Pipeline Status -->
  <div
    v-if="currentPipeline && currentPipeline.status"
    class="pipeline-status uk-card uk-card-default uk-card-small"
  >
    <div class="status-content">
      <span
        class="status-dot"
        :class="{
          running: currentPipeline.status === 'running',
          completed: currentPipeline.status === 'completed',
          failed: currentPipeline.status === 'failed',
        }"
      ></span>

      <span class="status-text">
        {{
          $t('text.pipeline.label') +
          ' ' +
          currentPipeline.id +
          ' ' +
          $t(`text.pipeline.status.${currentPipeline.status}`)
        }}
      </span>
    </div>
  </div>
  <!-- Deletion Confirmation -->
  <div id="del-confirm" uk-modal>
    <div class="uk-modal-dialog button-container uk-modal-body">
      <h2 class="uk-modal-title">{{ $t('text.nodeDeleteConfirm.title') }}</h2>
      <p>{{ $t('text.nodeDeleteConfirm.warning') }}</p>
      <p class="uk-text-right">
        <button class="uk-button uk-button-small uk-cancel-button uk-modal-close" type="button">
          {{ $t('btns.cancel') }}
        </button>
        <button
          class="uk-button uk-button-small uk-delete-button uk-modal-close"
          @click="deleteSelectedNodes"
          type="button"
        >
          {{ $t('btns.confirm') }}
        </button>
      </p>
    </div>
  </div>
  <!-- Run Pipeline Modal -->
  <div id="run-pipeline-modal" uk-modal="esc-close: false; bg-close: false">
    <div class="uk-modal-dialog button-container uk-modal-body">
      <h2 class="uk-modal-title">
        {{ $t('text.runPipeline.title') }}
      </h2>

      <p>
        {{ $t('text.runPipeline.description') }}
      </p>

      <div class="uk-margin">
        <label>
          <input type="checkbox" v-model="runForm.allowProducer" class="uk-switch" />
          {{ $t('text.runPipeline.allowProducer') }}
        </label>
      </div>

      <div v-if="runForm.allowProducer">
        <div class="uk-margin">
          <h4>{{ $t('text.runPipeline.nChannels') }}</h4>
          <input type="number" v-model.number="runForm.n_channels" class="uk-input" min="1" />
        </div>

        <div class="uk-margin">
          <h4>{{ $t('text.runPipeline.frequency') }}</h4>
          <input
            type="number"
            v-model.number="runForm.frequency"
            class="uk-input"
            min="0.1"
            step="0.1"
          />
        </div>
      </div>

      <div class="uk-margin">
        <h4>{{ $t('text.runPipeline.runtime') }}</h4>
        <input type="number" v-model.number="runForm.runtime" class="uk-input" min="5" required />
      </div>

      <p class="uk-text-right">
        <button class="uk-button uk-button-small uk-cancel-button uk-modal-close" type="button">
          {{ $t('btns.cancel') }}
        </button>

        <button
          class="uk-button uk-button-small uk-button-primary"
          type="button"
          @click="createRequest"
        >
          {{ $t('btns.runPipeline') }}
        </button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.vue-flow :deep(.vue-flow__minimap) {
  border: 1px solid black;
}

#additional-control-buttons {
  cursor: pointer;
  display: flex;
  width: 15px;
  background-color: #333333;
  padding: 5px;
  border-bottom: 1px solid var(--v-theme-on-surface);
}

/* Hover effect for dark mode */
.basic-flow.dark #additional-control-buttons:hover {
  background-color: #4d4d4d !important;
}

/* Hover effect for light mode */
.basic-flow:not(.dark) #additional-control-buttons:hover {
  background-color: #f4f4f4 !important;
}

#delete-button {
  height: 30px;
  background-color: var(--mkpError);
  color: white !important;
}

#view-results-button {
  height: 30px;
  color: white !important;
}

#view-results-button:disabled,
#delete-button:disabled {
  background-color: #979494;
  color: #999;
  cursor: not-allowed;
  border-color: #dae0e5;
  box-shadow: none;
}
</style>
