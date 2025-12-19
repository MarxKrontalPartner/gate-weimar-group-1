<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'

const { updateNodeData } = useVueFlow()
const showModal = ref(false)
const props = defineProps(['id', 'data', 'isDark'])

//props specifically for light/dark mode

const reactiveData = reactive(props.data)

const onModalToggle = () => {
  showModal.value = !showModal.value
}

const emit = defineEmits(['take-snapshot'])

const onSave = () => {
  updateNodeData(props.id, {
    code: reactiveData.code,
  })
  emit('take-snapshot')
  onModalToggle()
}

const editorOptions = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
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
      style="border-radius: 3px; width: auto"
    >
      Edit Code
    </button>

    <!-- This is the modal -->
    <div id="modal-example" uk-modal="esc-close: false; bg-close: false" v-if="showModal">
      <div class="uk-modal-dialog uk-modal-body">
        <h2 class="uk-modal-title">{{ reactiveData.content }}</h2>
        <div class="code-editor-container">
          <CodeEditor
            v-model:value="reactiveData.code"
            language="python"
            :theme="isDark ? 'vs-dark' : 'vs-light'"
            :options="editorOptions"
          />
        </div>
        <p class="uk-text-right">
          <button
            @click="onSave"
            class="uk-button uk-modal-close uk-save-button uk-button-small"
            type="button"
          >
            Save
          </button>
        </p>
      </div>
    </div>
  </div>

  <Handle type="source" :position="Position.Right" :connectable="1" />
</template>
