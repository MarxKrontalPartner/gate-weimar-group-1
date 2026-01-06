<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { useVueFlow } from '@vue-flow/core'
import { createOnInput, blockSpace, blockPaste } from '@/utils/nodeEventHandlers'

const { updateNodeData } = useVueFlow()
const props = defineProps<{
  id: string
  data: { content: string }
}>()

const onInput = createOnInput(updateNodeData, props.id)
</script>

<template>
  <div class="container dark">
    <input
      id="inputnode"
      :value="data.content"
      class="nodrag uk-input input-nodes"
      type="text"
      aria-label="Input"
      @input="onInput"
      @keydown="blockSpace"
      @paste="blockPaste"
    />
    <Handle type="source" :position="Position.Right" :connectable="1" />
  </div>
</template>
