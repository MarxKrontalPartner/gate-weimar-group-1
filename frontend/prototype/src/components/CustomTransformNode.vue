<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref, computed, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useRoute } from 'vue-router'

const { updateNodeData } = useVueFlow()
const showModal = ref(false)
const props = defineProps(['id', 'data', 'isDark'])

//props specifically for light/dark mode

const reactiveData = reactive(props.data)

const route = useRoute()
const isInTestArea = computed(() => route.name === 'test-area')

watch(
  () => props.data.code,
  (newVal) => {
    if (!showModal.value) {
      reactiveData.code = newVal ?? ''
    }
  },
)

const onModalToggle = () => {
  if (isInTestArea.value) {
    return
  }
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
  <div class="container dark">
    <Handle type="target" :position="Position.Left" :connectable="1" />
    <input
      type="text"
      v-model="reactiveData.content"
      class="nodrag uk-input input-nodes"
      name="transformation-name"
    />

    <button
      @click="onModalToggle"
      class="uk-button uk-button-primary uk-button-small"
      :uk-toggle="!isInTestArea ? 'target: #modal-example' : undefined"
      style="border-radius: 3px; width: auto"
    >
      Edit Code
    </button>

    <Teleport to="body">
      <div
        id="modal-example"
        uk-modal="esc-close: false; bg-close: false"
        v-if="showModal && !isInTestArea"
        class="uk-modal uk-open"
        style="display: block; background: rgba(0, 0, 0, 0.6)"
      >
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
    </Teleport>
  </div>

  <Handle type="source" :position="Position.Right" :connectable="1" />
</template>
