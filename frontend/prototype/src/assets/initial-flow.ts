import { type Node, type Edge } from '@vue-flow/core'

export const initialNodes: Node[] = [
  {
    id: '1',
    type: 'custom-input',
    data: { content: 'Input Topic' },
    position: { x: 0, y: 500 },
  },
  {
    id: '2',
    type: 'custom-transform',
    data: {
      content: 'Sum Transform',
      code: `def sum_transform(row: dict) -> dict:
    for key in row:
        if key.startswith("channel_"):
            row[key] += 10
    return row
  `,
    },
    position: { x: 300, y: 500 },
  },
  {
    id: '3',
    type: 'custom-intermediate',
    data: { content: 'Intermediate Topic' },
    position: { x: 600, y: 500 },
  },
  {
    id: '4',
    type: 'custom-transform',
    data: {
      content: 'Mul Transform',
      code: `def mul_transform(row: dict) -> dict:
    for key in row:
        if key.startswith("channel_"):
            row[key] *= 2
    return row
  `,
    },
    position: { x: 900, y: 500 },
  },
  {
    id: '5',
    type: 'custom-output',
    data: { content: 'Output Topic' },
    position: { x: 1200, y: 500 },
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
  {
    id: 'e4-5',
    source: '4',
    target: '5',
  },
]
