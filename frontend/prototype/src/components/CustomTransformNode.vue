<script setup lang="ts">
import { Position, Handle, useVueFlow } from '@vue-flow/core'
import { reactive, ref } from 'vue'
import TransformEditorModal from '@/components/TransformEditorModal.vue'

const { updateNodeData } = useVueFlow()
const props = defineProps(['id', 'data', 'isDark'])
const showModal = ref(false)
const reactiveData = reactive(props.data)

const onSave = (newCode: string) => {
  reactiveData.code = newCode
  updateNodeData(props.id, { code: newCode })
}
</script>

<template>
  <div class="container" :class="{ dark: isDark }">
    <Handle type="target" :position="Position.Left" :connectable="1" />
    <input v-model="reactiveData.content" class="nodrag uk-input input-nodes" />
    <button
      class="uk-button uk-button-primary uk-button-small edit-code-btn"
      @click="showModal = true"
    >
      Edit Code
    </button>
    <Handle type="source" :position="Position.Right" :connectable="1" />
  </div>

  <TransformEditorModal
    :show="showModal"
    :node-name="reactiveData.content || 'Transform'"
    :initial-code="reactiveData.code || ''"
    :is-dark="isDark"
    @save="onSave"
    @close="showModal = false"
  />
</template>
