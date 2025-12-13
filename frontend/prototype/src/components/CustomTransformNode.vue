<script setup lang="ts">
import { Position, Handle, useVueFlow } from '@vue-flow/core'
import { ref, watch, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import MonacoEditor from 'monaco-editor-vue3'

const props = defineProps<{
  id: string
  data: {
    content: string
    code?: string
  }
}>()

const { updateNodeData, findNode } = useVueFlow()
const route = useRoute()

// Detect if we are in the TestArea route
const isInTestArea = computed(() => route.name === 'test-area')

// Modal visibility
const showModal = ref(false)

// Local editable copy of the code
const code = ref<string>('')

// Initialize code on mount
onMounted(() => {
  code.value = props.data.code ?? ''
})

// Watch for external changes to props.data.code (e.g., sync from TestArea)
watch(
  () => props.data.code,
  (newVal) => {
    // Only update local copy if modal is closed (prevents overwriting user edits)
    if (!showModal.value) {
      code.value = newVal ?? ''
    }
  }
)

const onCodeButtonClick = (event: MouseEvent) => {
  if (isInTestArea.value) {
    // Let click bubble up in TestArea (parent handles node selection/execution)
    return
  }

  event.stopPropagation()

  // Ensure we have the absolute latest code from Vue Flow store
  const node = findNode(props.id)
  if (node?.data && typeof node.data === 'object') {
    const nodeData = node.data as { code?: string }
    code.value = nodeData.code ?? ''
  } else {
    code.value = props.data.code ?? ''
  }

  showModal.value = true
}

const onCloseModal = () => {
  showModal.value = false
}

const onSave = () => {
  updateNodeData(props.id, {
    content: props.data.content,
    code: code.value,
  })
  showModal.value = false
}

const handleEditorChange = (newValue: string) => {
  code.value = newValue
}

const editorOptions = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  tabSize: 4,
  insertSpaces: true,
}
</script>

<template>
  <div class="transform-node-container">
    <!-- Input Handle -->
    <Handle type="target" :position="Position.Left" :connectable="1" />

    <!-- Node Content -->
    <div class="transform-node-content">
      <p class="transform-title">{{ props.data.content }}</p>
      <button @click="onCodeButtonClick" class="code-button" type="button">
        CODE
      </button>
    </div>

    <!-- Output Handle -->
    <Handle type="source" :position="Position.Right" :connectable="1" />

    <!-- Modal (only shown outside TestArea) -->
    <Teleport to="body">
      <div
        v-if="showModal && !isInTestArea"
        class="modal-overlay"
        @click.self="onCloseModal"
      >
        <div class="modal-dialog">
          <div class="modal-header">
            <h2>{{ props.data.content }}</h2>
            <button class="modal-close-btn" @click="onCloseModal">
              &times;
            </button>
          </div>

          <div class="modal-body">
            <div class="code-editor-wrapper">
              <MonacoEditor
                :value="code"
                @change="handleEditorChange"
                language="python"
                theme="vs-dark"
                :options="editorOptions"
                class="code-editor"
              />
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-cancel" @click="onCloseModal">Cancel</button>
            <button class="btn-save" @click="onSave">Save</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.transform-node-container {
  position: relative;
}

.transform-node-content {
  background: #1e293b;
  border: 1px solid #475569;
  border-radius: 8px;
  padding: 12px 20px;
  min-width: 150px;
  text-align: center;
}

.transform-title {
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.code-button {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  padding: 6px 20px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.code-button:hover {
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  transform: translateY(-1px);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-dialog {
  background: #1e293b;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.5);
  border: 1px solid #475569;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #475569;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #f1f5f9;
}

.modal-close-btn {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-close-btn:hover {
  color: #fff;
}

.modal-body {
  flex: 1;
  padding: 16px 20px;
  overflow: hidden;
}

.code-editor-wrapper {
  height: 400px;
  border: 1px solid #475569;
  border-radius: 6px;
  overflow: hidden;
}

.code-editor {
  width: 100%;
  height: 100%;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #475569;
}

.btn-cancel,
.btn-save {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: #475569;
  color: #e2e8f0;
  border: none;
}

.btn-cancel:hover {
  background: #64748b;
}

.btn-save {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  border: none;
}

.btn-save:hover {
  background: linear-gradient(135deg, #4ade80, #22c55e);
}
</style>
