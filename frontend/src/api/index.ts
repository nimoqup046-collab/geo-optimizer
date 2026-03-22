import request from './request'

export interface BrandProfile {
  id: string
  workspace_id: string
  name: string
  industry: string
  service_description: string
  target_audience: string
  tone_of_voice: string
  call_to_action: string
  region: string
  competitors: string[]
  banned_words: string[]
  glossary: Record<string, string>
  platform_preferences: Record<string, any>
  content_boundaries: string
  created_at: string
  updated_at: string
}

export interface SourceAsset {
  id: string
  workspace_id: string
  brand_id: string
  title: string
  source_type: string
  platform: string
  file_name: string
  file_path: string
  mime_type: string
  raw_text: string
  summary: string
  tags: string[]
  status: string
  created_at: string
  updated_at: string
}

export interface AnalysisReport {
  report_id: string
  title: string
  keyword_layers: Record<string, any[]>
  gap_analysis: Record<string, any>
  recommendations: string[]
  llm_summary: string
  agent_team_report?: string | null
  created_at: string
}

export interface ContentVariant {
  id: string
  content_item_id: string
  platform: string
  title: string
  body: string
  summary: string
  tags: string[]
  llm_provider: string
  llm_model: string
  status: string
  created_at: string
}

export interface ContentItem {
  id: string
  workspace_id: string
  brand_id: string
  report_id: string
  content_type: string
  topic: string
  status: string
  version_no: number
  created_at: string
  updated_at: string
  variants: ContentVariant[]
}

export interface PublishTask {
  id: string
  workspace_id: string
  brand_id: string
  content_variant_id: string
  platform: string
  account_id?: string
  scheduled_at?: string
  status: string
  human_confirmation: string
  publish_url: string
  result_payload: Record<string, any>
  failure_reason: string
  created_at: string
  updated_at: string
}

export interface PerformanceSnapshot {
  id: string
  workspace_id: string
  brand_id: string
  publish_task_id?: string
  content_variant_id?: string
  keyword: string
  platform: string
  impressions: number
  reads: number
  likes: number
  favorites: number
  comments: number
  shares: number
  leads: number
  keyword_index: number
  notes: string
  created_at: string
  updated_at: string
}

export interface OptimizationInsight {
  id: string
  workspace_id: string
  brand_id: string
  source_snapshot_ids: string[]
  insight_type: string
  title: string
  details: string
  action_items: string[]
  created_at: string
}

export interface PromptProfile {
  id: string
  workspace_id: string
  name: string
  role: string
  platform: string
  industry: string
  tone_of_voice: string
  banned_words: string[]
  call_to_action: string
  system_prompt: string
  user_prompt_template: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowStep {
  id: string
  workspace_id: string
  brand_id?: string
  name: string
  step_type: string
  adapter: string
  status: string
  retry_count: number
  retry_limit: number
  input_payload: Record<string, any>
  output_payload: Record<string, any>
  config: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ReadinessCheck {
  ok: boolean
  detail: string
}

export interface ReadinessResponse {
  status: 'ok' | 'degraded'
  timestamp: string
  checks: Record<string, ReadinessCheck>
  feature_flags?: Record<string, boolean>
}

export interface DemoBootstrapResponse {
  workspace_id: string
  brand_id: string
  asset_id: string
  report_id: string
  content_id: string
  task_id: string
  performance_id: string
  insight_id: string
  bootstrapped_at: string
}

export interface DemoStatusResponse {
  ready: boolean
  workspace_id: string
  last_bootstrap_at: string | null
  counts: Record<string, number>
}

export interface WechatRichPostResponse {
  task_id: string
  status: string
  feature_enabled: boolean
  message: string
  generated_at: string
  payload: Record<string, any>
}

export interface WechatArticleResponse {
  task_id: string
  status: string
  title: string
  summary: string
  sections: Array<{ heading: string; body: string; image_directive: string }>
  cover_image_directive: string
  image_directives: Array<{ position: string; description: string }>
  tags: string[]
  cta: string
  word_count: number
  exports: Record<string, string>
  generated_at: string
}

export const brandApi = {
  list: () => request.get<BrandProfile[]>('/brands'),
  get: (id: string) => request.get<BrandProfile>(`/brands/${id}`),
  create: (payload: Partial<BrandProfile>) => request.post<BrandProfile>('/brands', payload),
  update: (id: string, payload: Partial<BrandProfile>) => request.put<BrandProfile>(`/brands/${id}`, payload)
}

export const assetApi = {
  list: (params?: { brand_id?: string; source_type?: string; platform?: string }) =>
    request.get<SourceAsset[]>('/assets', { params }),
  paste: (payload: any) => request.post<SourceAsset>('/assets/paste', payload),
  upload: (formData: FormData) =>
    request.post<SourceAsset>('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
}

export const analysisApi = {
  run: (payload: any) => request.post<AnalysisReport>('/analysis/run', payload),
  listReports: (params?: { brand_id?: string }) =>
    request.get<AnalysisReport[]>('/analysis/reports', { params }),
  exportReport: (reportId: string, format: 'md' | 'pdf') =>
    request.get(`/analysis/reports/${reportId}/export`, {
      params: { format },
      responseType: 'blob'
    })
}

export const contentApi = {
  generate: (payload: any) => request.post<ContentItem[]>('/content/generate', payload),
  list: (params?: { brand_id?: string; status?: string }) =>
    request.get<ContentItem[]>('/content', { params }),
  updateStatus: (id: string, payload: { status: string; reviewed_by?: string }) =>
    request.patch<ContentItem>(`/content/${id}/status`, payload),
  approve: (id: string) => request.patch<ContentItem>(`/content/${id}/status`, { status: 'approved' })
}

export const exportApi = {
  export: (payload: { content_item_ids: string[]; format: 'md' | 'html' | 'pdf' | 'pptx' | 'json' }) =>
    request.post('/exports', payload, { responseType: 'blob' })
}

export const publishApi = {
  list: (params?: { brand_id?: string; status?: string }) =>
    request.get<PublishTask[]>('/publish-tasks', { params }),
  create: (payload: any) => request.post<PublishTask>('/publish-tasks', payload),
  update: (id: string, payload: Partial<PublishTask>) =>
    request.patch<PublishTask>(`/publish-tasks/${id}`, payload)
}

export const performanceApi = {
  list: (params?: { brand_id?: string; platform?: string }) =>
    request.get<PerformanceSnapshot[]>('/performance', { params }),
  importData: (payload: any) => request.post<PerformanceSnapshot[]>('/performance/import', payload)
}

export const optimizationApi = {
  run: (payload: any) => request.post<OptimizationInsight[]>('/optimization-insights/run', payload),
  list: (params?: { brand_id?: string }) =>
    request.get<OptimizationInsight[]>('/optimization-insights', { params })
}

export const promptProfileApi = {
  list: (params?: { role?: string; platform?: string; industry?: string }) =>
    request.get<PromptProfile[]>('/prompt-profiles', { params }),
  create: (payload: any) => request.post<PromptProfile>('/prompt-profiles', payload),
  update: (id: string, payload: any) => request.put<PromptProfile>(`/prompt-profiles/${id}`, payload)
}

export interface StepMetrics {
  total: number
  idle: number
  running: number
  completed: number
  failed: number
  avg_duration_ms: number
  total_retries: number
  adapters: Record<string, number>
}

export const workflowStepApi = {
  list: (params?: { brand_id?: string; step_type?: string }) =>
    request.get<WorkflowStep[]>('/workflow-steps', { params }),
  create: (payload: any) => request.post<WorkflowStep>('/workflow-steps', payload),
  update: (id: string, payload: any) => request.patch<WorkflowStep>(`/workflow-steps/${id}`, payload),
  run: (id: string, payload?: { payload?: Record<string, any> }) =>
    request.post<WorkflowStep>(`/workflow-steps/${id}/run`, payload ?? {}),
  metrics: () => request.get<StepMetrics>('/workflow-steps/metrics'),
  adapters: () => request.get<string[]>('/workflow-steps/adapters')
}

export const creativeApi = {
  createWechatRichPost: (payload: {
    content_item_id: string
    variant_id?: string
    title_hint?: string
    style_hint?: string
  }) => request.post<WechatRichPostResponse>('/creative/wechat-rich-post', payload),
  generateFromTopic: (payload: {
    topic: string
    brand_name?: string
    tone_of_voice?: string
    call_to_action?: string
    banned_words?: string
    industry?: string
    style_hint?: string
    export_formats?: string[]
  }) => request.post<WechatArticleResponse>('/creative/wechat-generate', payload)
}

export const systemApi = {
  readiness: () => request.get<ReadinessResponse>('/system/readiness')
}

export const demoApi = {
  bootstrap: (payload?: { workspace_id?: string; force_reset?: boolean }) =>
    request.post<DemoBootstrapResponse>('/demo/bootstrap', payload ?? {}),
  status: () => request.get<DemoStatusResponse>('/demo/status')
}

// Compatibility exports for legacy pages.
export type Keyword = {
  id: string
  keyword: string
  category: string
  geo_score: number
  competition_level: string
  generated_content_count: number
  last_analyzed_at: string | null
}

export type Content = {
  id: string
  platform: string
  title: string
  content: string
  summary: string
  tags: string[]
  status: string
  llm_provider: string
  created_at: string
}

export type AnalysisResult = {
  keyword_id: string
  keyword: string
  geo_score: number
  search_opportunity: string
  competition_level: string
  recommendations: string[]
  related_keywords: string[]
  content_suggestions: string[]
}

// Re-export expert team API.
export { expertTeamApi } from './expertTeam'
export type {
  TeamReportResponse,
  ExpertRoleConfig,
  GEOScores,
  StrategyResult,
  ExpertOutput
} from './expertTeam'

// Re-export performance insights API.
export { performanceInsightsApi } from './performance'
export type {
  CorrelationItem,
  InsightItem,
  CorrelationResponse
} from './performance'

export const dataSourceApi = {
  providers: () => request.get<{ providers: any[] }>('/data-sources/providers'),
  fetch: (payload: { keywords: string[]; provider?: string }) =>
    request.post<{ metrics: any[]; count: number; source: string }>('/data-sources/fetch', payload),
  enrich: (payload: { keywords: string[]; provider?: string }) =>
    request.post<{ enriched: any[]; summary: any }>('/data-sources/enrich-analysis', payload),
}

export const rankingApi = {
  check: (payload: { keywords: string[]; platform?: string; geo_score?: number }) =>
    request.post<{ results: any[]; count: number }>('/ranking/check', payload),
  trends: (params?: { keyword?: string }) =>
    request.get<{ keyword: string; trends: any }>('/ranking/trends', { params }),
  actions: (params: { keyword: string; rank_position?: number; geo_score?: number }) =>
    request.get<{ actions: any[]; count: number }>('/ranking/actions', { params }),
}

export const competitorApi = {
  analyze: (payload: { competitor_names: string[]; keywords: string[] }) =>
    request.post<{ profiles: any[]; count: number }>('/competitors/analyze', payload),
  gaps: (payload: { keywords: string[]; competitor_names: string[] }) =>
    request.post<{ gaps: any[]; count: number; summary: any }>('/competitors/gaps', payload),
  benchmarks: (params?: { competitor_names?: string }) =>
    request.get<{ benchmarks: any[]; count: number }>('/competitors/benchmarks', { params }),
  strategy: (payload: { brand_name: string; competitor_names: string[]; keywords: string[] }) =>
    request.post<any>('/competitors/strategy', payload),
}

export const keywordApi = {
  getList: async (_params?: any) => [] as Keyword[],
  getDetail: async (_id: string) => ({} as Keyword),
  create: async (_data: any) => ({} as Keyword),
  update: async (_id: string, _data: any) => ({} as Keyword),
  delete: async (_id: string) => ({}),
  batchImport: async (_keywords: string[], _category?: string) => [] as Keyword[],
  analyze: async (_id: string, _deepAnalysis?: boolean) => ({} as AnalysisResult),
  batchAnalyze: async (_keywordIds: string[], _deepAnalysis?: boolean) => []
}
