<script setup lang="ts">
import { Position, Handle } from '@vue-flow/core'
import { useVueFlow } from '@vue-flow/core'

const { updateNodeData } = useVueFlow()
const props = defineProps(['id', 'data'])

const onInput = (event: InputEvent) => {
  const target = event.target as HTMLInputElement | null
  if (!target) {
    return
  }
  updateNodeData(props.id, {
    content: target.value,
  })
}
const blockSpace = (e: KeyboardEvent) => {
  if (e.key === ' ') {
    e.preventDefault()
  }
}

const blockPaste = (e: ClipboardEvent) => {
  const pasted = e.clipboardData?.getData('text') ?? ''

  if (/\s/.test(pasted)) {
    e.preventDefault()
  }
}
</script>

<template>
  <div class="container dark">
    <Handle type="target" :position="Position.Left" :connectable="1" />
    <input
      id="intermediatenode"
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
