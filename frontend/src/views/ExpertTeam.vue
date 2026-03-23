<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <!-- Team Configuration -->
    <n-card title="专家团队配置" :bordered="false">
      <n-space vertical>
        <n-descriptions bordered size="small" :column="3">
          <n-descriptions-item v-for="role in teamRoles" :key="role.role" :label="role.label">
            <n-tag :type="role.model.includes('claude') ? 'info' : 'success'" size="small">
              {{ role.model }}
            </n-tag>
          </n-descriptions-item>
        </n-descriptions>
        <n-text depth="3">
          编排流程：策略师 → 数据分析师 + GEO优化师（并行）→ 内容架构师 → 质量审核官
        </n-text>
      </n-space>
    </n-card>

    <!-- Run Expert Analysis -->
    <n-card title="运行专家团队分析" :bordered="false">
      <n-form :model="analysisForm">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="品牌">
              <n-select
                v-model:value="analysisForm.brand_id"
                :options="brandOptions"
                style="width: 100%"
                placeholder="选择品牌"
              />
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="目标平台">
              <n-select
                v-model:value="analysisForm.target_platforms"
                :options="platformOptions"
                multiple
                style="width: 100%"
              />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="关键词种子">
          <n-input
            v-model:value="analysisForm.keyword_input"
            type="textarea"
            :rows="3"
            placeholder="每行一个关键词"
          />
        </n-form-item>
        <n-form-item label="竞品关键词（可选）">
          <n-input
            v-model:value="analysisForm.competitor_input"
            type="textarea"
            :rows="2"
            placeholder="每行一个关键词"
          />
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="primary" :loading="analyzing" @click="runAnalysis">
          启动专家团队分析
        </n-button>
        <n-button :loading="loading" @click="load">刷新</n-button>
      </n-space>
    </n-card>

    <!-- GEO Score Radar Chart -->
    <n-card v-if="latestReport" title="GEO 评分卡" :bordered="false">
      <n-grid :cols="2" :x-gap="16">
        <n-grid-item>
          <div ref="radarChartRef" style="width: 100%; height: 320px" />
        </n-grid-item>
        <n-grid-item>
          <n-descriptions bordered size="small" :column="1">
            <n-descriptions-item label="综合评分">
              <n-tag :type="getScoreType(latestReport.geo_scores.overall)" size="large">
                {{ latestReport.geo_scores.overall.toFixed(1) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="可引用性 (Citability)">
              {{ latestReport.geo_scores.citability.toFixed(1) }}
            </n-descriptions-item>
            <n-descriptions-item label="断言密度 (Claim Density)">
              {{ latestReport.geo_scores.claim_density.toFixed(1) }}
            </n-descriptions-item>
            <n-descriptions-item label="可提取性 (Extractability)">
              {{ latestReport.geo_scores.extractability.toFixed(1) }}
            </n-descriptions-item>
            <n-descriptions-item label="可读性 (Readability)">
              {{ latestReport.geo_scores.readability.toFixed(1) }}
            </n-descriptions-item>
            <n-descriptions-item label="总耗时">
              {{ (latestReport.total_duration_ms / 1000).toFixed(1) }}s
            </n-descriptions-item>
          </n-descriptions>
        </n-grid-item>
      </n-grid>
    </n-card>

    <!-- Expert Reports Tabs -->
    <n-card v-if="latestReport" title="专家报告详情" :bordered="false">
      <n-tabs type="line" animated>
        <n-tab-pane
          v-for="(expert, key) in latestReport.experts"
          :key="key"
          :name="key"
          :tab="expert.label"
        >
          <n-space vertical>
            <n-space align="center">
              <n-tag :type="expert.model.includes('claude') ? 'info' : 'success'" size="small">
                {{ expert.model }}
              </n-tag>
              <n-text depth="3">耗时: {{ (expert.duration_ms / 1000).toFixed(1) }}s</n-text>
              <n-tag v-if="expert.error" type="error" size="small">错误</n-tag>
            </n-space>
            <div class="expert-content" v-html="renderMarkdown(expert.content)" />
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- GEO Content Optimizer -->
    <n-card title="GEO 内容优化工具" :bordered="false">
      <n-form>
        <n-form-item label="待优化内容">
          <n-input
            v-model:value="optimizeForm.content"
            type="textarea"
            :rows="5"
            placeholder="粘贴需要优化的内容..."
          />
        </n-form-item>
        <n-form-item label="优化策略">
          <n-select
            v-model:value="optimizeForm.strategies"
            :options="strategyOptions"
            multiple
            style="width: 100%"
          />
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="primary" :loading="optimizing" @click="runOptimize">执行优化</n-button>
        <n-button :loading="scoring" @click="runScore">计算 GEO 评分</n-button>
      </n-space>

      <n-card v-if="scoreResult" title="GEO 评分结果" style="margin-top: 12px" size="small">
        <n-space>
          <n-statistic label="综合" :value="scoreResult.overall.toFixed(1)" />
          <n-statistic label="可引用性" :value="scoreResult.citability.toFixed(1)" />
          <n-statistic label="断言密度" :value="scoreResult.claim_density.toFixed(1)" />
          <n-statistic label="可提取性" :value="scoreResult.extractability.toFixed(1)" />
          <n-statistic label="可读性" :value="scoreResult.readability.toFixed(1)" />
        </n-space>
      </n-card>

      <n-card
        v-for="(result, idx) in optimizeResults"
        :key="idx"
        :title="`策略: ${result.strategy_name}`"
        style="margin-top: 12px"
        size="small"
      >
        <n-space vertical>
          <n-text depth="3">{{ result.estimated_improvement }}</n-text>
          <n-collapse>
            <n-collapse-item title="优化后内容" name="content">
              <div class="expert-content" v-html="renderMarkdown(result.optimized_text)" />
            </n-collapse-item>
            <n-collapse-item title="变更说明" name="changes">
              <n-list bordered size="small">
                <n-list-item v-for="(change, cIdx) in result.changes_made" :key="cIdx">
                  {{ change }}
                </n-list-item>
              </n-list>
            </n-collapse-item>
          </n-collapse>
        </n-space>
      </n-card>
    </n-card>

    <!-- Historical Reports -->
    <n-card title="专家分析历史" :bordered="false">
      <n-data-table :columns="reportColumns" :data="historicalReports" />
      <n-empty v-if="historicalReports.length === 0" description="暂无专家分析报告" />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import { brandApi, analysisApi, type AnalysisReport } from '@/api'
import {
  expertTeamApi,
  type TeamReportResponse,
  type ExpertRoleConfig,
  type GEOScores,
  type StrategyResult
} from '@/api/expertTeam'

const message = useMessage()
const loading = ref(false)
const analyzing = ref(false)
const optimizing = ref(false)
const scoring = ref(false)
const loadError = ref('')

const brands = ref<any[]>([])
const teamRoles = ref<ExpertRoleConfig[]>([])
const latestReport = ref<TeamReportResponse | null>(null)
const historicalReports = ref<AnalysisReport[]>([])
const scoreResult = ref<GEOScores | null>(null)
const optimizeResults = ref<StrategyResult[]>([])
const radarChartRef = ref<HTMLElement | null>(null)
const radarChartInstance = ref<any | null>(null)

const brandOptions = computed(() =>
  brands.value.map((b) => ({ label: b.name, value: b.id }))
)

const platformOptions = [
  { label: '公众号', value: 'wechat' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '知乎', value: 'zhihu' },
  { label: '短视频脚本', value: 'video' }
]

const defaultStrategyOptions = [
  { label: '引用增强', value: 'citation_enhancement' },
  { label: '统计增强', value: 'statistics_addition' },
  { label: '问答结构化', value: 'qa_structuring' },
  { label: '断言前置', value: 'answer_frontloading' },
  { label: '实体丰富', value: 'entity_enrichment' }
]
const strategyOptions = ref(defaultStrategyOptions)

const analysisForm = reactive({
  brand_id: '',
  keyword_input: '',
  competitor_input: '',
  target_platforms: ['wechat', 'xiaohongshu', 'zhihu', 'video']
})

const optimizeForm = reactive({
  content: '',
  strategies: ['citation_enhancement']
})

const splitLines = (val: string) =>
  val.split('\n').map((s) => s.trim()).filter(Boolean)

function getScoreType(score: number): 'success' | 'warning' | 'error' {
  if (score >= 70) return 'success'
  if (score >= 50) return 'warning'
  return 'error'
}

function renderMarkdown(text: string): string {
  if (!text) return ''
  return sanitizeHtml(escapeHtml(text)
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>')
    .replace(/\n/g, '<br/>'))
}

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizeHtml(input: string): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(input, 'text/html')
  const blocked = new Set(['script', 'style', 'iframe', 'object', 'embed', 'link', 'meta', 'svg', 'math'])
  const allowedTag = new Set(['h2', 'h3', 'h4', 'strong', 'em', 'li', 'br', 'p', 'ul', 'ol', 'a', 'code', 'pre', 'blockquote'])
  const allowedAttrsByTag: Record<string, Set<string>> = {
    a: new Set(['href', 'title', 'target', 'rel'])
  }
  const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT)
  const toUnwrap: Element[] = []
  const toDrop: Element[] = []

  const safeHref = (href: string) => {
    const normalized = href.trim().toLowerCase()
    return (
      normalized.startsWith('http://') ||
      normalized.startsWith('https://') ||
      normalized.startsWith('mailto:') ||
      normalized.startsWith('#')
    )
  }

  while (walker.nextNode()) {
    const el = walker.currentNode as Element
    const tag = el.tagName.toLowerCase()
    if (blocked.has(tag)) {
      toDrop.push(el)
      continue
    }
    if (!allowedTag.has(tag)) {
      toUnwrap.push(el)
      continue
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase()
      const value = attr.value.trim()
      if (name.startsWith('on') || name === 'style') {
        el.removeAttribute(attr.name)
        continue
      }
      const allowedAttrs = allowedAttrsByTag[tag] || new Set<string>()
      if (!allowedAttrs.has(name)) {
        el.removeAttribute(attr.name)
        continue
      }
      if (tag === 'a' && name === 'href' && !safeHref(value)) {
        el.removeAttribute('href')
      }
    }
    if (tag === 'a') {
      if (!el.getAttribute('href')) {
        el.removeAttribute('target')
        el.removeAttribute('rel')
      } else {
        el.setAttribute('target', '_blank')
        el.setAttribute('rel', 'noopener noreferrer nofollow')
      }
    }
  }

  for (const el of toDrop) {
    el.remove()
  }
  for (const el of toUnwrap) {
    el.replaceWith(...Array.from(el.childNodes))
  }
  return doc.body.innerHTML
}

function renderRadarChart() {
  if (!radarChartRef.value || !latestReport.value) return
  try {
    const echarts = (window as any).echarts
    if (!echarts) return
    const existing = echarts.getInstanceByDom(radarChartRef.value)
    if (existing && !radarChartInstance.value) {
      radarChartInstance.value = existing
    }
    if (!radarChartInstance.value) {
      radarChartInstance.value = echarts.init(radarChartRef.value)
    }
    const chart = radarChartInstance.value
    const scores = latestReport.value.geo_scores
    chart.setOption({
      radar: {
        indicator: [
          { name: '可引用性', max: 100 },
          { name: '断言密度', max: 100 },
          { name: '可提取性', max: 100 },
          { name: '可读性', max: 100 }
        ],
        shape: 'circle'
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: [scores.citability, scores.claim_density, scores.extractability, scores.readability],
              name: 'GEO 评分',
              areaStyle: { opacity: 0.3 }
            }
          ]
        }
      ]
    })
  } catch {
    // ECharts not loaded yet, skip radar
  }
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [brandList, roles, reports, strategies] = await Promise.all([
      brandApi.list(),
      expertTeamApi.getRoles().catch(() => []),
      analysisApi.listReports(),
      expertTeamApi.getStrategies().catch(() => null)
    ])
    brands.value = brandList
    teamRoles.value = roles
    if (strategies?.strategies?.length) {
      strategyOptions.value = strategies.strategies.map((value: string) => ({
        value,
        label: strategies.descriptions?.[value] || value
      }))
    } else {
      strategyOptions.value = defaultStrategyOptions
    }
    historicalReports.value = reports.filter((r) => isExpertReport(r))
    if (!analysisForm.brand_id && brandList.length > 0) {
      analysisForm.brand_id = brandList[0].id
    }
  } catch (error: any) {
    loadError.value = `加载失败: ${error?.message || '未知错误'}`
  } finally {
    loading.value = false
  }
}

const runAnalysis = async () => {
  if (!analysisForm.brand_id) {
    message.warning('请先选择品牌')
    return
  }
  const seeds = splitLines(analysisForm.keyword_input)
  if (seeds.length === 0) {
    message.warning('请输入关键词')
    return
  }
  analyzing.value = true
  try {
    const report = await expertTeamApi.analyze({
      brand_id: analysisForm.brand_id,
      keyword_seeds: seeds,
      competitor_keywords: splitLines(analysisForm.competitor_input),
      target_platforms: analysisForm.target_platforms
    })
    latestReport.value = report
    message.success(`专家团队分析完成，耗时 ${(report.total_duration_ms / 1000).toFixed(1)}s`)
    await nextTick()
    renderRadarChart()
    await load()
  } catch (error: any) {
    message.error(`分析失败: ${error?.message || '未知错误'}`)
  } finally {
    analyzing.value = false
  }
}

const runScore = async () => {
  if (!optimizeForm.content.trim()) {
    message.warning('请输入内容')
    return
  }
  scoring.value = true
  try {
    scoreResult.value = await expertTeamApi.scoreContent(optimizeForm.content)
    message.success(`GEO 综合评分: ${scoreResult.value.overall.toFixed(1)}`)
  } catch (error: any) {
    message.error(`评分失败: ${error?.message || '未知错误'}`)
  } finally {
    scoring.value = false
  }
}

const runOptimize = async () => {
  if (!optimizeForm.content.trim()) {
    message.warning('请输入内容')
    return
  }
  optimizing.value = true
  try {
    optimizeResults.value = await expertTeamApi.optimize({
      content: optimizeForm.content,
      strategies: optimizeForm.strategies
    })
    message.success('优化完成')
  } catch (error: any) {
    message.error(`优化失败: ${error?.message || '未知错误'}`)
  } finally {
    optimizing.value = false
  }
}

const reportColumns = [
  { title: '标题', key: 'title' },
  {
    title: '创建时间',
    key: 'created_at',
    render: (row: AnalysisReport) => new Date(row.created_at).toLocaleString()
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: AnalysisReport) =>
      h(
        NButton,
        { size: 'small', onClick: () => message.info('报告ID: ' + row.report_id) },
        { default: () => '查看' }
      )
  }
]

watch(latestReport, () => {
  nextTick(renderRadarChart)
})

function isExpertReport(report: AnalysisReport): boolean {
  return report.report_type === 'expert_team' || report.title?.includes('专家') || false
}

onUnmounted(() => {
  if (radarChartInstance.value) {
    radarChartInstance.value.dispose()
    radarChartInstance.value = null
  }
})

onMounted(load)
</script>

<style scoped>
.expert-content {
  padding: 12px;
  background: var(--n-color-embedded);
  border-radius: 6px;
  line-height: 1.7;
  max-height: 500px;
  overflow-y: auto;
}
.expert-content h2,
.expert-content h3,
.expert-content h4 {
  margin: 12px 0 6px;
}
.expert-content li {
  margin-left: 20px;
}
</style>
