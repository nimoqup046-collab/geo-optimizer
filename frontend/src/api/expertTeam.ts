import request from './request'

export interface ExpertOutput {
  role: string
  label: string
  model: string
  content: string
  duration_ms: number
  error: string | null
}

export interface GEOScores {
  claim_density: number
  citability: number
  extractability: number
  readability: number
  overall: number
  details: Record<string, string>
}

export interface TeamReportResponse {
  report_id: string
  experts: Record<string, ExpertOutput>
  geo_scores: GEOScores
  total_duration_ms: number
  markdown_report: string
  created_at: string
}

export interface ExpertRoleConfig {
  role: string
  label: string
  model: string
  provider: string
}

export interface TeamConfig {
  roles: ExpertRoleConfig[]
  pipeline_order: string[]
  feature_enabled: boolean
}

export interface StrategyResult {
  strategy_name: string
  optimized_text: string
  changes_made: string[]
  estimated_improvement: string
}

export interface StrategyInfo {
  strategies: string[]
  descriptions: Record<string, string>
}

export const expertTeamApi = {
  getConfig: () => request.get<TeamConfig>('/expert-team/config'),

  getRoles: () => request.get<ExpertRoleConfig[]>('/expert-team/roles'),

  getStrategies: () => request.get<StrategyInfo>('/expert-team/strategies'),

  analyze: (payload: {
    brand_id: string
    keyword_seeds: string[]
    competitor_keywords?: string[]
    target_platforms?: string[]
    provider?: string
  }) => request.post<TeamReportResponse>('/expert-team/analyze', payload),

  runExpert: (payload: {
    role: string
    payload: Record<string, any>
    context?: Record<string, any>
    provider?: string
  }) => request.post<ExpertOutput>('/expert-team/expert/run', payload),

  scoreContent: (text: string) => request.post<GEOScores>('/expert-team/geo-score', { text }),

  optimize: (payload: {
    content: string
    strategies: string[]
    provider?: string
  }) => request.post<StrategyResult[]>('/expert-team/optimize', payload)
}
