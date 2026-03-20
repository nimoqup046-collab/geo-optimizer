<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <n-card :title="UI_TEXT.analysis.title" :bordered="false">
      <n-form :model="form">
        <n-form-item label="品牌">
          <n-select v-model:value="form.brand_id" :options="brandOptions" style="width: 320px" />
        </n-form-item>
        <n-form-item label="关键词种子">
          <n-input
            v-model:value="form.keyword_input"
            type="textarea"
            :rows="4"
            placeholder="每行一个关键词"
          />
        </n-form-item>
        <n-form-item label="竞品关键词（可选）">
          <n-input
            v-model:value="form.competitor_input"
            type="textarea"
            :rows="3"
            placeholder="每行一个关键词"
          />
        </n-form-item>
        <n-form-item :label="UI_TEXT.analysis.modelLabel">
          <n-select
            v-model:value="form.analysis_model"
            :options="analysisModelOptions"
            style="width: 320px"
            clearable
            :placeholder="UI_TEXT.analysis.modelDefault"
          />
        </n-form-item>
        <n-form-item>
          <n-space align="center">
            <n-switch v-model:value="form.use_agent_team" />
            <n-text>{{ UI_TEXT.analysis.agentTeamToggle }}</n-text>
          </n-space>
        </n-form-item>
        <n-form-item v-if="form.use_agent_team" label="专家选择（可选）">
          <n-checkbox-group v-model:value="form.agent_roles">
            <n-space>
              <n-checkbox
                v-for="agent in agentRoleOptions"
                :key="agent.value"
                :value="agent.value"
                :label="agent.label"
              />
            </n-space>
          </n-checkbox-group>
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="primary" :loading="running" @click="run">{{ UI_TEXT.analysis.run }}</n-button>
        <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
      </n-space>
    </n-card>

    <n-card :title="UI_TEXT.analysis.reports" :bordered="false">
      <n-data-table :columns="columns" :data="reports" />
      <n-empty v-if="reports.length === 0" description="暂无报告，先生成一份开始闭环。" />
    </n-card>

    <n-card v-if="activeReport" :title="UI_TEXT.analysis.detail" :bordered="false">
      <n-space vertical>
        <n-space justify="space-between" align="center">
          <n-text strong>{{ activeReport.title }}</n-text>
          <n-space>
            <n-button size="small" @click="exportReport('md')">导出报告 MD</n-button>
            <n-button size="small" @click="exportReport('pdf')">导出报告 PDF</n-button>
          </n-space>
        </n-space>

        <!-- GEO visibility score badge -->
        <n-space v-if="geoVisibilityScore !== null" align="center">
          <n-tag :type="geoVisibilityScore >= 0.6 ? 'success' : geoVisibilityScore >= 0.4 ? 'warning' : 'error'">
            {{ UI_TEXT.analysis.geoVisibility }}：{{ (geoVisibilityScore * 100).toFixed(0) }}%
          </n-tag>
        </n-space>

        <!-- Standard LLM summary -->
        <n-collapse>
          <n-collapse-item title="LLM 摘要" name="llm">
            <n-text style="white-space: pre-wrap">{{ activeReport.llm_summary }}</n-text>
          </n-collapse-item>
        </n-collapse>

        <!-- Agent team report (if available) -->
        <n-card
          v-if="activeReport.agent_team_report"
          :title="UI_TEXT.analysis.agentTeamReport"
          :bordered="true"
          style="margin-top: 8px"
        >
          <n-text style="white-space: pre-wrap; font-size: 13px">{{ activeReport.agent_team_report }}</n-text>
        </n-card>

        <n-list bordered>
          <n-list-item v-for="(recommendation, idx) in activeReport.recommendations" :key="idx">
            {{ recommendation }}
          </n-list-item>
        </n-list>
      </n-space>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { analysisApi, brandApi, type AnalysisReport } from '@/api'
import { UI_TEXT } from '@/constants/uiText'

const message = useMessage()
const running = ref(false)
const loading = ref(false)
const loadError = ref('')
const brands = ref<any[]>([])
const reports = ref<AnalysisReport[]>([])
const activeReport = ref<AnalysisReport | null>(null)

const form = reactive({
  brand_id: '',
  keyword_input: '婚姻关系修复\n信任重建\n冲突沟通',
  competitor_input: '',
  use_agent_team: false,
  agent_roles: [] as string[],
  analysis_model: null as string | null
})

const analysisModelOptions = [
  { label: UI_TEXT.analysis.modelClaude, value: 'anthropic/claude-sonnet-4-5' },
  { label: UI_TEXT.analysis.modelGemini, value: 'google/gemini-2.5-pro-preview' }
]

const agentRoleOptions = [
  { label: 'GEO策略专家', value: 'geo_strategist' },
  { label: '内容质量专家', value: 'content_quality' },
  { label: '数据分析专家', value: 'data_analytics' },
  { label: '竞品情报专家', value: 'competitor_intel' }
]

const brandOptions = computed(() =>
  brands.value.map((brand) => ({ label: brand.name, value: brand.id }))
)

const geoVisibilityScore = computed(() => {
  const gap = activeReport.value?.gap_analysis
  if (!gap) return null
  return typeof gap.geo_visibility_score === 'number' ? gap.geo_visibility_score : null
})

const splitLines = (value: string) =>
  value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)

const downloadBlob = (blob: Blob, fileName: string) => {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  window.URL.revokeObjectURL(url)
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    brands.value = await brandApi.list()
    if (!form.brand_id && brands.value.length > 0) form.brand_id = brands.value[0].id
    reports.value = await analysisApi.listReports(form.brand_id ? { brand_id: form.brand_id } : undefined)
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

const run = async () => {
  if (!form.brand_id) {
    message.warning('请先选择品牌')
    return
  }
  running.value = true
  try {
    const result = await analysisApi.run({
      brand_id: form.brand_id,
      keyword_seeds: splitLines(form.keyword_input),
      competitor_keywords: splitLines(form.competitor_input),
      use_agent_team: form.use_agent_team,
      agent_roles: form.agent_roles.length > 0 ? form.agent_roles : undefined,
      analysis_model: form.analysis_model || undefined
    })
    message.success('报告已生成')
    await load()
    // Auto-open the freshly generated report from the reloaded list.
    const found = reports.value.find((r) => r.report_id === result.report_id)
    activeReport.value = found ?? result
  } catch (error: any) {
    message.error(`生成失败：${error?.message || UI_TEXT.common.unknownError}`)
  } finally {
    running.value = false
  }
}

const exportReport = async (format: 'md' | 'pdf') => {
  if (!activeReport.value) return
  try {
    const blob: Blob = await analysisApi.exportReport(activeReport.value.report_id, format)
    downloadBlob(blob, `analysis_report_${activeReport.value.report_id}.${format}`)
    message.success(`报告已导出为 ${format.toUpperCase()}`)
  } catch (error: any) {
    message.error(`导出失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const columns = [
  { title: '标题', key: 'title' },
  {
    title: 'GEO 可见性',
    key: 'geo_visibility',
    render: (row: AnalysisReport) => {
      const score = row.gap_analysis?.geo_visibility_score
      return typeof score === 'number' ? `${(score * 100).toFixed(0)}%` : '-'
    }
  },
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
        { size: 'small', onClick: () => (activeReport.value = row) },
        { default: () => '查看' }
      )
  }
]

onMounted(load)
</script>
