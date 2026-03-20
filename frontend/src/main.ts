import { createApp, defineComponent, h, onErrorCaptured, ref } from 'vue'
import { createPinia } from 'pinia'

type FatalSource =
  | 'bootstrap'
  | 'window.error'
  | 'window.unhandledrejection'
  | 'router.error'
  | 'vue.errorHandler'
  | 'error-boundary'

interface FatalState {
  source: FatalSource
  message: string
  timestamp: string
}

const ROUTER_FATAL_EVENT = 'geo:router-fatal'
const fatalState = ref<FatalState | null>(null)

let hasMountedApp = false
let guardsInstalled = false

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.stack || error.message
  if (typeof error === 'string') return error
  try {
    return JSON.stringify(error, null, 2)
  } catch {
    return String(error)
  }
}

function escapeHtml(input: string): string {
  return input
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function mountFatalToDom(state: FatalState): void {
  const root = document.getElementById('app')
  if (!root) return

  const escapedSource = escapeHtml(state.source)
  const escapedTime = escapeHtml(state.timestamp)
  const escapedMessage = escapeHtml(state.message)

  root.innerHTML = `
    <div style="font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif; padding: 24px;">
      <h2 style="margin: 0 0 12px 0;">页面加载失败</h2>
      <p style="margin: 0 0 8px 0; color: #666;">前端发生致命异常，已触发兜底保护并阻止白屏。</p>
      <p style="margin: 0 0 16px 0; color: #999; font-size: 12px;">来源：${escapedSource} | 时间：${escapedTime}</p>
      <pre style="white-space: pre-wrap; background: #f8f8f8; padding: 12px; border-radius: 8px; border: 1px solid #eee;">${escapedMessage}</pre>
      <button onclick="window.location.reload()" style="margin-top: 12px; border: 0; background: #18a058; color: white; padding: 8px 12px; border-radius: 6px; cursor: pointer;">
        刷新重试
      </button>
    </div>
  `
}

function reportFatal(source: FatalSource, error: unknown, info?: string): void {
  const baseMessage = normalizeError(error)
  const message = info && info.trim().length > 0 ? `${baseMessage}\n\n[Vue info] ${info}` : baseMessage
  const nextState: FatalState = {
    source,
    message,
    timestamp: new Date().toLocaleString()
  }
  fatalState.value = nextState
  console.error(`[geo-frontend][${source}]`, error)
  if (!hasMountedApp) mountFatalToDom(nextState)
}

function installGlobalGuards(): void {
  if (guardsInstalled) return
  guardsInstalled = true

  window.addEventListener('error', (event) => {
    reportFatal('window.error', event?.error || event?.message || 'unknown error')
  })
  window.addEventListener('unhandledrejection', (event) => {
    event.preventDefault()
    const reason = (event as PromiseRejectionEvent).reason
    reportFatal('window.unhandledrejection', reason)
  })
  window.addEventListener(ROUTER_FATAL_EVENT, (event) => {
    const detail = (event as CustomEvent).detail
    reportFatal('router.error', detail)
  })
}

const FatalFallback = defineComponent({
  name: 'FatalFallback',
  setup() {
    return () => {
      if (!fatalState.value) return null
      const state = fatalState.value
      return h(
        'div',
        {
          style:
            "font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif; padding: 24px;"
        },
        [
          h('h2', { style: 'margin: 0 0 12px 0;' }, '页面加载失败'),
          h('p', { style: 'margin: 0 0 8px 0; color: #666;' }, '前端发生致命异常，已触发 Error Boundary 兜底。'),
          h(
            'p',
            { style: 'margin: 0 0 16px 0; color: #999; font-size: 12px;' },
            `来源：${state.source} | 时间：${state.timestamp}`
          ),
          h(
            'pre',
            {
              style:
                'white-space: pre-wrap; background: #f8f8f8; padding: 12px; border-radius: 8px; border: 1px solid #eee;'
            },
            state.message
          ),
          h(
            'button',
            {
              style:
                'margin-top: 12px; border: 0; background: #18a058; color: white; padding: 8px 12px; border-radius: 6px; cursor: pointer;',
              onClick: () => window.location.reload()
            },
            '刷新重试'
          )
        ]
      )
    }
  }
})

const AppErrorBoundary = defineComponent({
  name: 'AppErrorBoundary',
  setup(_, { slots }) {
    onErrorCaptured((error, _instance, info) => {
      reportFatal('error-boundary', error, info)
      return false
    })
    return () => (fatalState.value ? h(FatalFallback) : slots.default?.())
  }
})

async function bootstrap() {
  installGlobalGuards()
  try {
    const [{ default: App }, { default: router }] = await Promise.all([
      import('./App.vue'),
      import('./router')
    ])

    const Root = defineComponent({
      name: 'RootEntry',
      setup() {
        return () =>
          h(AppErrorBoundary, null, {
            default: () => h(App)
          })
      }
    })

    const app = createApp(Root)
    app.config.errorHandler = (error, _instance, info) => {
      reportFatal('vue.errorHandler', error, info)
    }

    app.use(createPinia())
    app.use(router)
    app.mount('#app')
    hasMountedApp = true
  } catch (error) {
    reportFatal('bootstrap', error)
  }
}

void bootstrap()
