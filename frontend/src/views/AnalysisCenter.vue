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
            <n-button size="small" type="info" :loading="expertAnalyzing" @click="runExpertAnalysis">
              专家深度分析
            </n-button>
            <n-button size="small" @click="exportReport('md')">导出报告 MD</n-button>
            <n-button size="small" @click="exportReport('pdf')">导出报告 PDF</n-button>
          </n-space>
        </n-space>

        <!-- GEO Score Display -->
        <n-card v-if="geoScores" size="small" title="GEO 评分">
          <n-grid :cols="5" :x-gap="8">
            <n-grid-item>
              <n-statistic label="综合" :value="geoScores.overall.toFixed(1)" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="可引用性" :value="geoScores.citability.toFixed(1)" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="断言密度" :value="geoScores.claim_density.toFixed(1)" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="可提取性" :value="geoScores.extractability.toFixed(1)" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="可读性" :value="geoScores.readability.toFixed(1)" />
            </n-grid-item>
          </n-grid>
        </n-card>

        <n-text>{{ activeReport.llm_summary }}</n-text>
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
import { expertTeamApi, type GEOScores } from '@/api/expertTeam'
import { UI_TEXT } from '@/constants/uiText'

const message = useMessage()
const running = ref(false)
const loading = ref(false)
const expertAnalyzing = ref(false)
const loadError = ref('')
const brands = ref<any[]>([])
const reports = ref<AnalysisReport[]>([])
const activeReport = ref<AnalysisReport | null>(null)
const geoScores = ref<GEOScores | null>(null)

const form = reactive({
  brand_id: '',
  keyword_input: '婚姻关系修复\n信任重建\n冲突沟通',
  competitor_input: ''
})

const brandOptions = computed(() =>
  brands.value.map((brand) => ({ label: brand.name, value: brand.id }))
)

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
    await analysisApi.run({
      brand_id: form.brand_id,
      keyword_seeds: splitLines(form.keyword_input),
      competitor_keywords: splitLines(form.competitor_input)
    })
    message.success('报告已生成')
    await load()
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

const runExpertAnalysis = async () => {
  if (!form.brand_id) {
    message.warning('请先选择品牌')
    return
  }
  const seeds = splitLines(form.keyword_input)
  if (seeds.length === 0) {
    message.warning('请输入关键词')
    return
  }
  expertAnalyzing.value = true
  try {
    const report = await expertTeamApi.analyze({
      brand_id: form.brand_id,
      keyword_seeds: seeds,
      competitor_keywords: splitLines(form.competitor_input)
    })
    geoScores.value = report.geo_scores
    message.success(`专家团队分析完成，综合评分: ${report.geo_scores.overall.toFixed(1)}`)
    await load()
  } catch (error: any) {
    message.error(`专家分析失败: ${error?.message || '未知错误'}`)
  } finally {
    expertAnalyzing.value = false
  }
}

const columns = [
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
        { size: 'small', onClick: () => (activeReport.value = row) },
        { default: () => '查看' }
      )
  }
]

onMounted(load)
</script>
