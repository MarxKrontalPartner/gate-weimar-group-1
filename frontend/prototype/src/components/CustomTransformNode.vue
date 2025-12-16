<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { CodeEditor } from 'monaco-editor-vue3'
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useRoute } from 'vue-router'

const { updateNodeData, findNode } = useVueFlow()
const showModal = ref(false)
const props = defineProps(['id', 'data', 'isDark'])

//props specifically for light/dark mode

const reactiveData = reactive(props.data)

// ===== ADDITIONS START =====
const route = useRoute()

// Detect if we are in the TestArea route
// IMPORTANT: This must match the route name in router/index.ts
const isInTestArea = computed(() => route.name === 'test-area')

// Local editable copy of the code (prevents reactivity conflicts)
const localCode = ref<string>('')

// Initialize code on mount
onMounted(() => {
  localCode.value = reactiveData.code ?? ''
})

// Watch for external changes to props.data.code (e.g., sync from TestArea)
watch(
  () => props.data.code,
  (newVal) => {
    // Only update local copy if modal is closed (prevents overwriting user edits)
    if (!showModal.value) {
      localCode.value = newVal ?? ''
      reactiveData.code = newVal ?? ''
    }
  },
)

// Sync localCode back to reactiveData when localCode changes
const handleEditorChange = (newValue: string) => {
  localCode.value = newValue
  reactiveData.code = newValue  // Keep reactiveData in sync
}

// Explicit close function
const onCloseModal = () => {
  showModal.value = false
}
// ===== ADDITIONS END =====

const onModalToggle = () => {
  // ===== ADDITION: Check if in TestArea =====
  if (isInTestArea.value) {
    // In TestArea, don't open modal - let parent handle it
    return
  }

  // ===== ADDITION: Sync latest code before opening =====
  if (!showModal.value) {
    const node = findNode(props.id)
    if (node?.data && typeof node.data === 'object') {
      const nodeData = node.data as { code?: string }
      localCode.value = nodeData.code ?? ''
      reactiveData.code = nodeData.code ?? ''
    }
  }
  // ===== END ADDITION =====

  showModal.value = !showModal.value
}

const onSave = () => {
  // ===== ADDITION: Sync localCode to reactiveData before saving =====
  reactiveData.code = localCode.value
  // ===== END ADDITION =====

  updateNodeData(props.id, {
    code: reactiveData.code,  // UNCHANGED - still uses reactiveData.code
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

    <!-- FIX: Only apply uk-toggle when NOT in TestArea -->
    <!-- In TestArea, clicking this button lets the event bubble to VueFlow's node-click handler -->
    <button
      @click="onModalToggle"
      class="uk-button uk-button-primary uk-button-small"
      :data-uk-toggle="!isInTestArea ? 'target: #modal-example' : undefined"
      style="border-radius: 3px; width: auto"
    >
      Edit Code
    </button>

    <!-- ADDITION: Wrapped in Teleport, added !isInTestArea condition -->
    <Teleport to="body">
      <div
        id="modal-example"
        uk-modal="esc-close: false; bg-close: false"
        v-if="showModal && !isInTestArea"
        class="uk-modal uk-open"
        style="display: block; background: rgba(0,0,0,0.6);"
      >
        <div class="uk-modal-dialog uk-modal-body">
          <h2 class="uk-modal-title">{{ reactiveData.content }}</h2>
          <div class="code-editor-container">
            <!-- CHANGE: Use localCode with handleEditorChange for better sync -->
            <CodeEditor
              :value="localCode"
              @change="handleEditorChange"
              language="python"
              :theme="isDark ? 'vs-dark' : 'vs-light'"
              :options="editorOptions"
            />
          </div>
          <p class="uk-text-right">
            <!-- ADDITION: Cancel button -->
            <button
              @click="onCloseModal"
              class="uk-button uk-button-default uk-button-small"
              type="button"
              style="margin-right: 10px;"
            >
              Cancel
            </button>
            <!-- UNCHANGED: Same save button -->
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
