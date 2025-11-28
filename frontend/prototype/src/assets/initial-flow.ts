import { type Node, type Edge } from '@vue-flow/core'

export const initialNodes: Node[] = [
  {
    id: '1',
    type: 'custom-input',
    data: { content: 'Input Topic' },
    position: { x: 20, y: 500 },
  },
  {
    id: '2',
    type: 'custom-transform',
    data: {
      content: 'Transform 1',
      code: `def transform1(row: dict) -> dict:
    logger.info(f"before :: row :: {row}")
    for key in row:
        if key.startswith("channel_"):
            row[key] += 10
    logger.info(f"after :: row :: {row}")
    return row
  `,
    },
    position: { x: 300, y: 500 },
  },
  {
    id: '3',
    type: 'custom-transform',
    data: {
      content: 'Transform 2',
      code: `def transform2(row: dict) -> dict:
    logger.info(f"before :: row :: {row}")
    for key in row:
        if key.startswith("channel_"):
            row[key] += 10
    logger.info(f"after :: row :: {row}")
    return row
  `,
    },
    position: { x: 500, y: 500 },
  },
  {
    id: '4',
    type: 'custom-output',
    data: { content: 'Output Topic' },
    position: { x: 700, y: 500 },
  },
]

export const initialEdges: Edge[] = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
  },
  {
    id: 'e2-3',
    source: '2',
    target: '3',
  },
  {
    id: 'e3-4',
    source: '3',
    target: '4',
  },
]
