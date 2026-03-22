<template>
  <n-space vertical :size="18">
    <n-card title="SEO 页面审计" :bordered="false">
      <n-space align="center">
        <n-input
          v-model:value="auditUrl"
          placeholder="输入要审计的页面 URL"
          style="width: 480px"
          clearable
        />
        <n-select
          v-model:value="pageType"
          :options="pageTypeOptions"
          style="width: 140px"
        />
        <n-button type="primary" :loading="loading" :disabled="!auditUrl" @click="runAudit">
          开始审计
        </n-button>
      </n-space>
    </n-card>

    <template v-if="report">
      <!-- Score Overview -->
      <n-grid :cols="6" :x-gap="12">
        <n-grid-item>
          <n-statistic label="综合评分">
            <n-number-animation :from="0" :to="report.scores.overall" />
            <template #suffix>/100</template>
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="标题优化">
            <n-number-animation :from="0" :to="report.scores.title_optimization" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="Meta Description">
            <n-number-animation :from="0" :to="report.scores.meta_description" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="标题结构">
            <n-number-animation :from="0" :to="report.scores.heading_structure" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="内容质量">
            <n-number-animation :from="0" :to="report.scores.content_quality" />
          </n-statistic>
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="技术 SEO">
            <n-number-animation :from="0" :to="report.scores.technical_seo" />
          </n-statistic>
        </n-grid-item>
      </n-grid>

      <!-- Strengths -->
      <n-card v-if="report.strengths.length" title="优势" :bordered="false">
        <n-space vertical>
          <n-tag v-for="(s, i) in report.strengths" :key="i" type="success" size="medium">
            {{ s }}
          </n-tag>
        </n-space>
      </n-card>

      <!-- Issues -->
      <n-card v-if="report.issues.length" title="发现的问题" :bordered="false">
        <n-data-table :columns="issueColumns" :data="report.issues" :bordered="false" size="small" />
      </n-card>

      <!-- Recommendations -->
      <n-card v-if="report.recommendations.length" title="改进建议" :bordered="false">
        <n-data-table :columns="recColumns" :data="report.recommendations" :bordered="false" size="small" />
      </n-card>
    </template>

    <n-alert v-if="error" type="error" :show-icon="true" closable @close="error = ''">
      {{ error }}
    </n-alert>
  </n-space>
</template>

<script setup lang="ts">
import { h, ref } from 'vue'
import { NTag } from 'naive-ui'
import { seoAuditApi } from '@/api/seoAudit'
import type { SEOAuditReport } from '@/api/seoAudit'

const auditUrl = ref('')
const pageType = ref('article')
const loading = ref(false)
const error = ref('')
const report = ref<SEOAuditReport | null>(null)

const pageTypeOptions = [
  { label: '文章页', value: 'article' },
  { label: '落地页', value: 'landing' },
  { label: '产品页', value: 'product' },
  { label: '首页', value: 'homepage' }
]

const severityType = (s: string) => (s === 'P0' ? 'error' : s === 'P1' ? 'warning' : 'info')

const issueColumns = [
  {
    title: '严重度',
    key: 'severity',
    width: 80,
    render: (row: any) => h(NTag, { type: severityType(row.severity), size: 'small' }, () => row.severity)
  },
  { title: '类别', key: 'category', width: 100 },
  { title: '当前状态', key: 'current_state' },
  { title: '建议', key: 'suggestion' }
]

const recColumns = [
  { title: '优先级', key: 'priority', width: 80 },
  { title: '类别', key: 'category', width: 100 },
  { title: '操作建议', key: 'action' },
  { title: '预期影响', key: 'expected_impact', width: 80 }
]

async function runAudit() {
  if (!auditUrl.value) return
  loading.value = true
  error.value = ''
  report.value = null
  try {
    report.value = await seoAuditApi.audit(auditUrl.value, pageType.value)
  } catch (e: any) {
    error.value = e.message || '审计失败'
  } finally {
    loading.value = false
  }
}
</script>
