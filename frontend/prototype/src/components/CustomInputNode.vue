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
  <div class="container">
    <div class="dark">
      <input
        id="inputnode"
        :placeholder="data.content"
        class="nodrag uk-input input-nodes"
        type="text"
        aria-label="Input"
        @input="onInput"
      />
    </div>
    <Handle type="source" :position="Position.Right" :connectable="1" />
  </div>
</template>
