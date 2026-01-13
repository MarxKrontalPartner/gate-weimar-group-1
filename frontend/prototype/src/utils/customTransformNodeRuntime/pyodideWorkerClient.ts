import PyodideWorker from '@/workers/pyodideWorker?worker'
import { ref } from 'vue'

export const runtimeStatus = ref<'idle' | 'loading' | 'ready' | 'executing' | 'error'>('idle')

export type PyodideExecutionResult =
  | {
      stdout: string
      output: unknown
      error?: undefined
    }
  | {
      stdout: string
      error: {
        type: string
        msg: string
        line?: number
      }
    }

type WorkerResult =
  | { type: 'ready' }
  | { type: 'result'; payload: unknown }
  | { type: 'error'; payload: { message?: string } }

class PyodideWorkerClient {
  private worker: Worker | null = null
  private timeoutId: number | null = null
  private initializing: Promise<void> | null = null

  async init(): Promise<void> {
    // If already initialized or initializing → reuse
    if (this.worker) return
    if (this.initializing) return this.initializing

    runtimeStatus.value = 'loading'

    this.initializing = new Promise(async (resolve, reject) => {
      try {
        this.worker = new PyodideWorker()

        this.worker.onmessage = (e: MessageEvent<WorkerResult>) => {
          if (e.data.type === 'ready') {
            this.initializing = null
            runtimeStatus.value = 'ready'
            resolve()
          }
        }

        this.worker.onerror = (err) => {
          this.initializing = null
          this.worker = null
          runtimeStatus.value = 'error'
          reject(err)
        }

        this.worker.postMessage({ type: 'init' })
      } catch (e) {
        this.initializing = null
        runtimeStatus.value = 'error'
        reject(e)
      }
    })

    return this.initializing
  }

  run(
    code: string,
    input: Record<string, unknown>,
    timeoutMs: number,
  ): Promise<PyodideExecutionResult> {
    if (!this.worker) {
      throw new Error('Pyodide runtime not initialized')
    }

    runtimeStatus.value = 'executing'

    return new Promise((resolve, reject) => {
      this.timeoutId = window.setTimeout(() => {
        this.timeoutId = null
        this.terminate()
        reject(new Error('Execution timed out'))
      }, timeoutMs)

      this.worker!.onmessage = (e: MessageEvent<WorkerResult>) => {
        if (this.timeoutId !== null) {
          clearTimeout(this.timeoutId)
          this.timeoutId = null
        }

        runtimeStatus.value = 'ready'

        if (e.data.type === 'result') {
          const payload = e.data.payload
          if (typeof payload !== 'object' || payload === null || !('stdout' in payload)) {
            reject(new Error('Invalid worker result payload'))
            return
          } else resolve(payload as PyodideExecutionResult)
        } else if (e.data.type === 'error') {
          reject(new Error(e.data.payload?.message ?? 'Unknown worker error'))
        } else {
          reject(new Error('Unexpected worker message'))
        }
      }

      this.worker!.postMessage({ type: 'run', payload: { code, input } })
    })
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate()
      this.worker = null
    }

    if (this.timeoutId !== null) {
      clearTimeout(this.timeoutId)
      this.timeoutId = null
    }

    runtimeStatus.value = 'idle'
    this.initializing = null
  }

  isReady(): boolean {
    return this.worker !== null
  }
}

// EXPORT A SINGLE INSTANCE
export const pyodideWorkerClient = new PyodideWorkerClient()
