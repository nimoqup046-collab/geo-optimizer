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

    <n-grid :cols="4" :x-gap="12">
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.brands" :value="stats.brands" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.assets" :value="stats.assets" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.reports" :value="stats.reports" /></n-grid-item>
      <n-grid-item><n-statistic :label="UI_TEXT.overview.cards.contents" :value="stats.contents" /></n-grid-item>
    </n-grid>

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
  type DemoStatusResponse,
  type ReadinessResponse
} from '@/api'
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
  contents: 0
})

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

const formatTime = (value: string) => new Date(value).toLocaleString()

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [brands, assets, reportList, contents, tasks, insightList, readinessData, ds] =
      await Promise.all([
        brandApi.list(),
        assetApi.list(),
        analysisApi.listReports(),
        contentApi.list(),
        publishApi.list(),
        optimizationApi.list(),
        systemApi.readiness(),
        fetchDemoStatus()
      ])

    stats.value = {
      brands: brands.length,
      assets: assets.length,
      reports: reportList.length,
      contents: contents.length
    }
    reports.value = reportList
    insights.value = insightList
    readiness.value = readinessData
    demoStatus.value = ds

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
