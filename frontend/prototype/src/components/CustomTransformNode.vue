<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'

const { updateNodeData } = useVueFlow()
const showModal = ref(false)
const props = defineProps(['id', 'data'])

const reactiveData = reactive(props.data)

const onModalToggle = () => {
  showModal.value = !showModal.value
}

const onSave = () => {
  updateNodeData(props.id, {
    code: reactiveData.code,
  })
  onModalToggle()
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
      <p>{{ reactiveData.content }}</p>

      <!-- This is a button toggling the modal -->
      <button
        @click="onModalToggle"
        class="uk-button uk-button-primary uk-button-small"
        uk-toggle="target: #modal-example"
      >
        Code
      </button>

      <!-- This is the modal -->
      <div id="modal-example" uk-modal="esc-close: false; bg-close: false" v-if="showModal">
        <div class="uk-modal-dialog uk-modal-body">
          <h2 class="uk-modal-title">{{ reactiveData.content }}</h2>
          <div class="code-editor-container">
            <CodeEditor
              v-model:value="reactiveData.code"
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
