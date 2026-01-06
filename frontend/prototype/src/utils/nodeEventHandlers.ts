// src/utils/nodeEventHandlers.ts

export const createOnInput =
  (updateNodeData: (id: string, data: { content: string }) => void, nodeId: string) =>
  (event: Event) => {
    const target = event.target as HTMLInputElement | null
    if (!target) return

    updateNodeData(nodeId, {
      content: target.value,
    })
  }

export const blockSpace = (e: KeyboardEvent) => {
  if (e.key === ' ') {
    e.preventDefault()
  }
}

export const blockPaste = (e: ClipboardEvent) => {
  const pasted = e.clipboardData?.getData('text') ?? ''
  if (/\s/.test(pasted)) {
    e.preventDefault()
  }
}
