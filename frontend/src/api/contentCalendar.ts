import request from './request'

export interface CalendarEntry {
  priority: string
  content_topic: string
  target_keywords: string[]
  content_type: string
  target_platform: string
  suggested_week: number
  brief: string
}

export interface ContentCalendarResult {
  topic: string
  entries: CalendarEntry[]
  summary: string
}

export interface TopicClusterResult {
  topic: string
  clusters: Array<{
    pillar: {
      title: string
      core_keyword: string
      description: string
      word_count_target: number
    }
    cluster_pages: Array<{
      title: string
      target_keyword: string
      content_type: string
      search_intent: string
      link_anchor_text: string
    }>
    internal_link_strategy: string
  }>
  summary: string
}

export interface KeywordResearchResult {
  topic: string
  trending_keywords: Array<{
    keyword: string
    search_intent: string
    heat_level: number
    commercial_value: string
    reasoning: string
  }>
  commercial_keywords: Array<{
    keyword: string
    buyer_stage: string
    competition: string
    content_angle: string
  }>
  long_tail_opportunities: Array<{
    keyword: string
    parent_keyword: string
    search_intent: string
    ai_citation_potential: string
    suggested_format: string
  }>
  geo_suggestions: Array<{
    keyword: string
    strategy: string
    action: string
    expected_improvement: string
  }>
  summary: string
}

export const keywordResearchApi = {
  research(topic: string, brandName?: string, industry?: string, competitors?: string[]): Promise<KeywordResearchResult> {
    return request.post('/keywords/research', {
      topic,
      brand_name: brandName,
      industry,
      competitors: competitors || []
    })
  },

  buildClusters(topic: string, keywords?: string[], brandName?: string, industry?: string, maxClusters?: number): Promise<TopicClusterResult> {
    return request.post('/keywords/clusters', {
      topic,
      keywords: keywords || [],
      brand_name: brandName,
      industry,
      max_clusters: maxClusters || 3
    })
  },

  generateCalendar(topic: string, keywords?: string[], brandName?: string, industry?: string, weeks?: number): Promise<ContentCalendarResult> {
    return request.post('/keywords/calendar', {
      topic,
      keywords: keywords || [],
      brand_name: brandName,
      industry,
      weeks: weeks || 4
    })
  }
}
