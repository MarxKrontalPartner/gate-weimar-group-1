<script setup lang="ts">
import { Position, Handle, useVueFlow } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { ref, watch } from 'vue'

const props = defineProps<{
  id: string
  data: {
    content: string
    code?: string
  }
}>()

const { updateNodeData } = useVueFlow()

const showModal = ref(false)

// local editable copy of the code, initialised from props
const code = ref<string>(props.data.code ?? '')

// keep local code in sync with props when graph is updated externally (e.g. from TestArea)
watch(
  () => props.data.code,
  (newVal) => {
    code.value = newVal ?? ''
  },
  { immediate: true },
)

const onModalToggle = () => {
  showModal.value = !showModal.value
}

const onSave = () => {
  updateNodeData(props.id, {
    ...props.data,
    code: code.value,
  })
  showModal.value = false
}

const editorOptions = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
}
</script>

<template>
  <div class="container">
    <Handle type="target" :position="Position.Left" :connectable="1" />

    <div class="dark">
      <p class="title">{{ props.data.content }}</p>

      <!-- Button exactly as in your original UI -->
      <button
        @click="onModalToggle"
        class="uk-button uk-button-primary uk-button-small"
        uk-toggle="target: #modal-example"
      >
        CODE
      </button>

      <!-- Modal with Monaco editor -->
      <div id="modal-example" uk-modal="esc-close: false; bg-close: false" v-if="showModal">
        <div class="uk-modal-dialog uk-modal-body">
          <h2 class="uk-modal-title">{{ props.data.content }}</h2>

          <div class="code-editor-container">
            <CodeEditor
              v-model:value="code"
              language="python"
              theme="vs-dark"
              :options="editorOptions"
            />
          </div>

          <p class="uk-text-right">
            <button
              @click="onSave"
              class="uk-button uk-modal-close uk-button-primary uk-button-small"
              type="button"
            >
              Save
            </button>
          </p>
        </div>
      </div>
    </div>

    <Handle type="source" :position="Position.Right" :connectable="1" />
  </div>
</template>

<style scoped></style>
