import request from './request'

export interface CorrelationItem {
  dimension: string
  avg_score: number
  avg_engagement: number
  sample_count: number
  insight: string
}

export interface InsightItem {
  title: string
  description: string
  action_items: string[]
  supporting_data: Record<string, any>
}

export interface CorrelationResponse {
  correlations: CorrelationItem[]
  insights: InsightItem[]
  total_records: number
}

export const performanceInsightsApi = {
  getCorrelation: (params?: { brand_id?: string }) =>
    request.get<CorrelationResponse>('/performance/correlation', { params }),
}
