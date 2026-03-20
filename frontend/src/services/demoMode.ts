const DEMO_REAL_MODE_KEY = 'geo_real_mode'
const DEMO_BOOTSTRAPPED_KEY = 'geo_demo_bootstrapped'

export function isDemoModeEnabledByEnv(): boolean {
  const raw = String(import.meta.env.VITE_DEMO_MODE ?? '1').trim()
  return raw !== '0' && raw.toLowerCase() !== 'false'
}

export function isRealMode(): boolean {
  return localStorage.getItem(DEMO_REAL_MODE_KEY) === '1'
}

export function setRealMode(enabled: boolean): void {
  if (enabled) {
    localStorage.setItem(DEMO_REAL_MODE_KEY, '1')
    return
  }
  localStorage.removeItem(DEMO_REAL_MODE_KEY)
}

export function isDemoModeActive(): boolean {
  return isDemoModeEnabledByEnv() && !isRealMode()
}

export function markDemoBootstrapped(): void {
  localStorage.setItem(DEMO_BOOTSTRAPPED_KEY, '1')
}

export function clearDemoBootstrapped(): void {
  localStorage.removeItem(DEMO_BOOTSTRAPPED_KEY)
}

export function hasBootstrappedDemo(): boolean {
  return localStorage.getItem(DEMO_BOOTSTRAPPED_KEY) === '1'
}
