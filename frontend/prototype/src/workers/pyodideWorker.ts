/// <reference lib="webworker" />

import { loadPyodide } from 'pyodide'
import type { PyodideInterface } from 'pyodide'
import { buildExecutionCode } from '@/utils/customTransformNodeRuntime/pythonExecutor'

let pyodide: PyodideInterface | null = null

async function ensurePyodide(): Promise<PyodideInterface> {
  if (!pyodide) {
    const basePath = 'https://cdn.jsdelivr.net/pyodide/v0.29.1/full/'

    try {
      pyodide = await loadPyodide({
        indexURL: basePath,
      })
    } catch (err) {
      console.error(
        'Failed to load Pyodide from public/pyodide folder, make sure files exist:',
        err,
      )
      throw err
    }
  }
  return pyodide
}

self.onmessage = async (e) => {
  const { type, payload } = e.data

  try {
    if (type === 'init') {
      await ensurePyodide()
      self.postMessage({ type: 'ready' })
      return
    }

    if (type === 'run') {
      const { code, input } = payload
      const py = await ensurePyodide()

      py.globals.set('__user_code', code)
      py.globals.set('__input_data', JSON.stringify(input))

      const result = await py.runPythonAsync(buildExecutionCode())

      const jsResult =
        result && typeof result === 'object' && 'toJs' in result
          ? result.toJs({ dict_converter: Object.fromEntries })
          : result

      self.postMessage({ type: 'result', payload: jsResult })
      return
    }
  } catch (err: unknown) {
    self.postMessage({
      type: 'error',
      payload: {
        message: err instanceof Error ? err.message : String(err),
      },
    })
  }
}
