import { demoApi, type DemoBootstrapResponse, type DemoStatusResponse } from '@/api'

export async function runDemoSeed(forceReset = false): Promise<DemoBootstrapResponse> {
  return demoApi.bootstrap({ force_reset: forceReset })
}

export async function fetchDemoStatus(): Promise<DemoStatusResponse> {
  return demoApi.status()
}
