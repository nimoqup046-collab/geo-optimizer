import request from './request'

export interface SEOScores {
  title_optimization: number
  meta_description: number
  heading_structure: number
  content_quality: number
  technical_seo: number
  overall: number
}

export interface SEOIssue {
  severity: string
  category: string
  current_state: string
  suggestion: string
  code_example?: string
}

export interface SEORecommendation {
  priority: number
  category: string
  action: string
  expected_impact: string
}

export interface SEOAuditReport {
  target_url: string
  page_type: string
  scores: SEOScores
  strengths: string[]
  issues: SEOIssue[]
  recommendations: SEORecommendation[]
  summary: string
}

export const seoAuditApi = {
  audit(url: string, pageType: string = 'article'): Promise<SEOAuditReport> {
    return request.post('/seo-audit', { url, page_type: pageType })
  }
}
