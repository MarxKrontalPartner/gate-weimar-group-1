<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import {
  ConnectionMode,
  VueFlow,
  useVueFlow,
  Panel,
  type Edge,
  type FlowExportObject,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { ControlButton, Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { initialEdges, initialNodes } from '@/assets/initial-flow.ts'
import CustomIcon from '../components/CustomIcon.vue'
import CustomTransformNode from '@/components/CustomTransformNode.vue'
import CustomInputNode from '@/components/CustomInputNode.vue'
import CustomOutputNode from '@/components/CustomOutputNode.vue'
import AppBar from '@/components/AppBar.vue'
import UIkit from 'uikit'
import CustomIntermediateNode from '@/components/CustomIntermediateNode.vue'
import { type Payload } from '@/assets/payload.ts'

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
  getSelectedEdges,
  getSelectedNodes,
  setViewport,
} = useVueFlow()

const nodesData = ref(initialNodes)

const edgesData = ref(initialEdges)

// our dark mode toggle flag
const dark = ref(true)

/**
 * This is a Vue Flow event-hook which can be listened to from anywhere you call the composable, instead of only on the main component
 * Any event that is available as `@event-name` on the VueFlow component is also available as `onEventName` on the composable and vice versa
 *
 * onInit is called when the VueFlow viewport is initialized
 */
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

/**
 * To update a node or multiple nodes, you can
 * 1. Mutate the node objects *if* you're using `v-model`
 * 2. Use the `updateNode` method (from `useVueFlow`) to update the node(s)
 * 3. Create a new array of nodes and pass it to the `nodes` ref
 */
// function updatePos() {
//   nodes.value = nodes.value.map((node: Node) => {
//     return {
//       ...node,
//       position: {
//         x: Math.random() * 400,
//         y: Math.random() * 400,
//       },
//     }
//   })
// }

/**
 * toObject transforms your current graph data to an easily persist-able object
 */
// function logToObject() {
//   console.log(toObject())
// }

/**
 * Resets the current viewport transformation (zoom & pan)
 */
// function resetTransform() {
//   setViewport({ x: 0, y: 0, zoom: 1 })
// }

function toggleDarkMode() {
  dark.value = !dark.value
}

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

  nodesData.value.push({
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

  nodesData.value.push({
    id,
    position: { x: 400, y: 500 },
    type: 'custom-intermediate',
    data: { content: 'Intermediate Topic' },
  })
}

const createRequest = async () => {
  const obj = toObject()
  let transformations: string[] = []
  const payload: Payload[] = []

  const inputNode = obj.nodes.find((n) => n.type == 'custom-input')
  const outputNode = obj.nodes.find((n) => n.type == 'custom-output')

  if (!inputNode || !outputNode) {
    alert('input or output node missing')
    return
  }

  const tempPayload: Payload = {
    input_topic: inputNode.data.content,
    output_topic: outputNode.data.content,
    transformations: [],
    allow_producer: false,
    n_channels: 10,
    frequency: 1,
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
        alert('graph not connected')
        return
      }
      tempPayload.transformations = transformations
      payload.push({ ...tempPayload })
      break
    }
  }

  // -------------------------
  // Ask user whether to allow producer
  // -------------------------
  const allow_producer = confirm('Allow producer? OK = True, Cancel = False')

  payload.forEach((p) => {
    p.allow_producer = allow_producer
  })

  console.log('Sending payload:', payload)

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
      const msg = await res.text()
      alert('Backend error: ' + msg)
      return
    }

    const result = await res.json()
    console.log('Backend response:', result)
    alert('Pipeline started successfully!')
  } catch (err) {
    console.error(err)
    alert('Failed to contact backend.')
  }
}

const onRun = () => {
  createRequest()
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

const deleteSelectedElements = () => {
  const selectedNodes = getSelectedNodes.value
  const selectedEdges = getSelectedEdges.value
  if (selectedNodes.length > 0) {
    removeNodes(selectedNodes)
  }

  if (selectedEdges.length > 0) {
    removeEdges(selectedEdges)
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

watch([nodesData, edgesData], debounce(addToHistory, 500), { deep: true })

const applyState = async (state: FlowExportObject) => {
  nodesData.value = state.nodes || []

  await nextTick()

  edgesData.value = state.edges || []

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
</script>

<template>
  <VueFlow
    v-model="nodesData"
    :edges="edgesData"
    :class="{ dark }"
    class="basic-flow"
    :default-viewport="{ zoom: 1 }"
    :min-zoom="0.2"
    :max-zoom="4"
    @edge-double-click="removeEdge"
    :connection-mode="ConnectionMode.Strict"
    :delete-key-code="null"
  >
    <AppBar :is-dark="dark" />
    <Panel position="bottom-center">
      <div class="panel">
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="addNode">
          Add transformation node
        </button>
        <button
          class="uk-button uk-button-primary uk-button-small"
          type="button"
          @click="addIntermediateNode"
        >
          Add intermediate node
        </button>
      </div></Panel
    >
    <Panel position="top-center" style="margin-top: 75px">
      <div class="panel">
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="onRun">
          Run
        </button>
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="onExport">
          Export
        </button>
        <input id="fileUpload" type="file" accept="application/json" @change="uploadJson" hidden />
        <button class="uk-button uk-button-primary uk-button-small" type="button" @click="onImport">
          Import
        </button>
        <button
          class="uk-button uk-button-small"
          id="delete-button"
          @click="delConfirm"
          :disabled="getSelectedNodes.length === 0"
        >
          Delete Selected Nodes
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
      <ControlButton @click="toggleDarkMode">
        <CustomIcon v-if="dark" name="sun" />
        <CustomIcon v-else name="moon" />
      </ControlButton>
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
  <div id="del-confirm" uk-modal>
    <div class="uk-modal-dialog uk-modal-body" style="border-radius: 10px">
      <h2 class="uk-modal-title">Delete Node Confirmation</h2>
      <p>Are you sure you want to delete the selected Nodes?</p>
      <p class="uk-text-right">
        <button class="uk-button uk-cancel-button uk-modal-close" type="button">Cancel</button>
        <button
          class="uk-button uk-delete-button uk-modal-close"
          @click="deleteSelectedElements"
          type="button"
        >
          Confirm
        </button>
      </p>
    </div>
  </div>
</template>

<style scoped>
.vue-flow :deep(.vue-flow__minimap) {
  border: 2px solid black;
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
</style>
