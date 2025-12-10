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
</script>

<template>
  <div class="container dark">
    <input
      id="outputnode"
      :value="data.content"
      class="nodrag uk-input input-nodes"
      type="text"
      aria-label="Input"
      @input="onInput"
    />
    <Handle type="target" :position="Position.Left" :connectable="1" />
  </div>
</template>
