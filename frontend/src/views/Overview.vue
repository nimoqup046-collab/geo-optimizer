<template>
  <n-space vertical :size="18">
    <n-alert v-if="loadError" type="error" :show-icon="false">
      {{ loadError }}
    </n-alert>

    <n-card title="演示控制台" :bordered="false">
      <n-space align="center">
        <n-tag :type="demoStatus?.ready ? 'success' : 'warning'">
          {{ demoStatus?.ready ? UI_TEXT.demo.statusReady : UI_TEXT.demo.statusNotReady }}
        </n-tag>
        <n-text depth="3">
          最近引导时间：{{ demoStatus?.last_bootstrap_at ? formatTime(demoStatus.last_bootstrap_at) : '-' }}
        </n-text>
      </n-space>
      <n-space style="margin-top: 12px">
        <n-button type="primary" :loading="seeding" @click="seedDemoData(false)">
          {{ UI_TEXT.demo.bootstrap }}
        </n-button>
        <n-button :loading="resetting" @click="seedDemoData(true)">
          {{ UI_TEXT.demo.reset }}
        </n-button>
        <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
      </n-space>
    </n-card>

    <n-grid :cols="5" :x-gap="12">
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.brands" :value="stats.brands" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.assets" :value="stats.assets" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.reports" :value="stats.reports" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.contents" :value="stats.contents" /></n-grid-item>
      <n-grid-item><n-statistic label="专家报告" :value="stats.expertReports" /></n-grid-item>
    </n-grid>

    <!-- Expert Team Status -->
    <n-card title="专家团队" :bordered="false">
      <n-space align="center">
        <n-tag :type="expertTeamEnabled ? 'success' : 'warning'">
          {{ expertTeamEnabled ? '已启用' : '未启用' }}
        </n-tag>
        <n-text depth="3">
          模型: Claude Sonnet 4.6 + Gemini 3.1 Pro (via OpenRouter)
        </n-text>
      </n-space>
      <n-descriptions
        v-if="expertRoles.length > 0"
        bordered
        size="small"
        :column="3"
        style="margin-top: 12px"
      >
        <n-descriptions-item v-for="role in expertRoles" :key="role.role" :label="role.label">
          <n-tag :type="role.model.includes('claude') ? 'info' : 'success'" size="small">
            {{ role.model.split('/').pop() }}
          </n-tag>
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-card :title="UI_TEXT.overview.readiness.title" :bordered="false">
      <n-space align="center">
        <n-tag :type="readiness.status === 'ok' ? 'success' : 'warning'">
          {{
            readiness.status === 'ok'
              ? UI_TEXT.overview.readiness.statusOk
              : UI_TEXT.overview.readiness.statusDegraded
          }}
        </n-tag>
        <n-text depth="3">{{ readiness.timestamp || UI_TEXT.overview.readiness.unknown }}</n-text>
      </n-space>
      <n-descriptions
        v-if="Object.keys(readiness.checks).length > 0"
        bordered
        size="small"
        :column="2"
        style="margin-top: 12px"
      >
        <n-descriptions-item
          v-for="(check, key) in readiness.checks"
          :key="key"
          :label="String(key)"
        >
          <n-tag :type="check.ok ? 'success' : 'warning'">{{ check.ok ? '正常' : '告警' }}</n-tag>
          <n-text depth="3" style="margin-left: 8px">{{ check.detail }}</n-text>
        </n-descriptions-item>
      </n-descriptions>
    </n-card>

    <n-card :title="UI_TEXT.overview.queue.title" :bordered="false">
      <n-space>
        <n-tag type="default">{{ UI_TEXT.overview.queue.queued }}: {{ taskStats.queued }}</n-tag>
        <n-tag type="warning">{{ UI_TEXT.overview.queue.scheduled }}: {{ taskStats.scheduled }}</n-tag>
        <n-tag type="success">{{ UI_TEXT.overview.queue.posted }}: {{ taskStats.posted }}</n-tag>
        <n-tag type="error">{{ UI_TEXT.overview.queue.failed }}: {{ taskStats.failed }}</n-tag>
      </n-space>
    </n-card>

    <!-- Performance Insights -->
    <n-card title="效果反馈闭环" :bordered="false">
      <n-space align="center" style="margin-bottom: 12px">
        <n-tag :type="perfData.total_records > 0 ? 'success' : 'warning'">
          {{ perfData.total_records > 0 ? `${perfData.total_records} 条关联数据` : '暂无关联数据' }}
        </n-tag>
        <n-text depth="3">GEO 评分 × 内容效果关联分析</n-text>
      </n-space>
      <n-grid :cols="2" :x-gap="12" v-if="perfData.insights.length > 0">
        <n-grid-item v-for="(insight, idx) in perfData.insights" :key="idx">
          <n-card size="small" :bordered="true">
            <template #header>{{ insight.title }}</template>
            <n-text>{{ insight.description }}</n-text>
            <n-list size="small" style="margin-top: 8px">
              <n-list-item v-for="(action, aIdx) in insight.action_items" :key="aIdx">
                <n-text depth="2">{{ action }}</n-text>
              </n-list-item>
            </n-list>
          </n-card>
        </n-grid-item>
      </n-grid>
      <n-empty v-else description="录入内容效果数据后，系统将自动分析 GEO 评分与效果的关联" />
    </n-card>

    <n-grid :cols="2" :x-gap="12">
      <n-grid-item>
        <n-card :title="UI_TEXT.overview.latestReports" :bordered="false">
          <n-list bordered>
            <n-list-item v-for="report in reports.slice(0, 5)" :key="report.report_id">
              <n-thing :title="report.title">
                <template #description>{{ formatTime(report.created_at) }}</template>
              </n-thing>
            </n-list-item>
            <n-empty v-if="reports.length === 0" description="暂无报告" />
          </n-list>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card :title="UI_TEXT.overview.latestInsights" :bordered="false">
          <n-list bordered>
            <n-list-item v-for="insight in insights.slice(0, 5)" :key="insight.id">
              <n-thing :title="insight.title">
                <template #description>{{ insight.details }}</template>
              </n-thing>
            </n-list-item>
            <n-empty v-if="insights.length === 0" description="暂无优化建议" />
          </n-list>
        </n-card>
      </n-grid-item>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  analysisApi,
  assetApi,
  brandApi,
  contentApi,
  optimizationApi,
  publishApi,
  systemApi,
  performanceInsightsApi,
  type AnalysisReport,
  type DemoStatusResponse,
  type ReadinessResponse,
  type CorrelationResponse
} from '@/api'
import { expertTeamApi, type ExpertRoleConfig } from '@/api/expertTeam'
import { UI_TEXT } from '@/constants/uiText'
import { fetchDemoStatus, runDemoSeed } from '@/services/demoSeed'

const message = useMessage()
const loading = ref(false)
const seeding = ref(false)
const resetting = ref(false)
const loadError = ref('')

const stats = ref({
  brands: 0,
  assets: 0,
  reports: 0,
  contents: 0,
  expertReports: 0
})
const expertTeamEnabled = ref(false)
const expertRoles = ref<ExpertRoleConfig[]>([])

const taskStats = ref({
  queued: 0,
  scheduled: 0,
  posted: 0,
  failed: 0
})

const readiness = ref<ReadinessResponse>({
  status: 'degraded',
  timestamp: '',
  checks: {}
})

const demoStatus = ref<DemoStatusResponse | null>(null)
const reports = ref<any[]>([])
const insights = ref<any[]>([])
const perfData = ref<CorrelationResponse>({ correlations: [], insights: [], total_records: 0 })

const formatTime = (value: string) => new Date(value).toLocaleString()

const isExpertReport = (report: AnalysisReport) =>
  report.report_type === 'expert_team' || report.title?.includes('专家') || false

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [brands, assets, reportList, contents, tasks, insightList, readinessData, ds, teamConfig, perfCorrelation] =
      await Promise.all([
        brandApi.list(),
        assetApi.list(),
        analysisApi.listReports(),
        contentApi.list(),
        publishApi.list(),
        optimizationApi.list(),
        systemApi.readiness(),
        fetchDemoStatus(),
        expertTeamApi.getConfig().catch(() => ({ feature_enabled: false, roles: [] })),
        performanceInsightsApi.getCorrelation().catch(() => ({ correlations: [], insights: [], total_records: 0 }))
      ])

    stats.value = {
      brands: brands.length,
      assets: assets.length,
      reports: reportList.length,
      contents: contents.length,
      expertReports: reportList.filter((r) => isExpertReport(r)).length
    }
    expertTeamEnabled.value = teamConfig.feature_enabled
    expertRoles.value = teamConfig.roles || []
    reports.value = reportList
    insights.value = insightList
    readiness.value = readinessData
    demoStatus.value = ds
    perfData.value = perfCorrelation as CorrelationResponse

    taskStats.value = {
      queued: tasks.filter((task) => task.status === 'queued').length,
      scheduled: tasks.filter((task) => task.status === 'scheduled').length,
      posted: tasks.filter((task) => task.status === 'posted').length,
      failed: tasks.filter((task) => task.status === 'failed').length
    }
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

const seedDemoData = async (forceReset: boolean) => {
  if (forceReset) resetting.value = true
  else seeding.value = true
  try {
    await runDemoSeed(forceReset)
    message.success(forceReset ? '演示数据已重置' : '演示闭环数据已生成')
    await load()
  } catch (error: any) {
    message.error(`演示操作失败：${error?.message || UI_TEXT.common.unknownError}`)
  } finally {
    seeding.value = false
    resetting.value = false
  }
}

onMounted(load)
</script>
