import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const CHUNK_RELOAD_KEY = 'geo_chunk_reload_once'
const ROUTER_FATAL_EVENT = 'geo:router-fatal'

type AsyncViewLoader = () => Promise<unknown>

function lazyView(loader: AsyncViewLoader): AsyncViewLoader {
  return () =>
    loader().catch((error) => {
      const message = error instanceof Error ? error.message : String(error)
      throw new Error(`[RouteImportError] ${message}`)
    })
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: lazyView(() => import('@/views/Layout.vue')),
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        name: 'Overview',
        component: lazyView(() => import('@/views/Overview.vue')),
        meta: { title: '总览' }
      },
      {
        path: 'brands',
        name: 'Brands',
        component: lazyView(() => import('@/views/Brands.vue')),
        meta: { title: '品牌档案' }
      },
      {
        path: 'assets',
        name: 'Assets',
        component: lazyView(() => import('@/views/Assets.vue')),
        meta: { title: '素材池' }
      },
      {
        path: 'analysis',
        name: 'AnalysisCenter',
        component: lazyView(() => import('@/views/AnalysisCenter.vue')),
        meta: { title: '分析中心' }
      },
      {
        path: 'workshop',
        name: 'Workshop',
        component: lazyView(() => import('@/views/Workshop.vue')),
        meta: { title: '内容工坊' }
      },
      {
        path: 'distribution',
        name: 'DistributionFeedback',
        component: lazyView(() => import('@/views/DistributionFeedback.vue')),
        meta: { title: '分发与反馈' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.onError((error) => {
  const message = String(error?.message || error || '')
  const isChunkError =
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('Importing a module script failed')

  if (isChunkError) {
    const hasReloaded = sessionStorage.getItem(CHUNK_RELOAD_KEY) === '1'
    if (hasReloaded) {
      sessionStorage.removeItem(CHUNK_RELOAD_KEY)
    } else {
      sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
      window.location.reload()
      return
    }
  }

  window.dispatchEvent(
    new CustomEvent(ROUTER_FATAL_EVENT, {
      detail: message
    })
  )
})

router.afterEach(() => {
  sessionStorage.removeItem(CHUNK_RELOAD_KEY)
})

export default router
