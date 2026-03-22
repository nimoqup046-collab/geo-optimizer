<template>
  <n-space vertical :size="16">
    <n-card title="竞品内容分析">
      <n-alert type="info" title="功能说明" style="margin-bottom: 12px">
        分析竞品内容策略，发现内容缺口和差异化机会，制定超越竞品的内容战略。
      </n-alert>

      <n-space vertical :size="12">
        <n-input
          v-model:value="competitorInput"
          placeholder="输入竞品名称（多个用逗号分隔）"
        />
        <n-input
          v-model:value="keywordInput"
          placeholder="输入关键词（多个用逗号分隔）"
        />
        <n-space>
          <n-button type="primary" :loading="loadingAnalysis" @click="runAnalysis">运行分析</n-button>
          <n-button :loading="loadingStrategy" :disabled="!profiles.length" @click="genStrategy">生成差异化策略</n-button>
        </n-space>
      </n-space>
    </n-card>

    <n-card v-if="profiles.length" title="竞品画像">
      <n-data-table
        :columns="profileColumns"
        :data="profiles"
        :bordered="false"
        size="small"
      />
    </n-card>

    <n-grid v-if="gaps.length" :cols="2" :x-gap="12" :y-gap="12">
      <n-gi :span="2">
        <n-card title="内容缺口分析">
          <n-space style="margin-bottom: 8px">
            <n-statistic label="总缺口数" :value="gaps.length" />
            <n-statistic label="未覆盖" :value="gapSummary.by_type?.uncovered || 0" />
            <n-statistic label="弱覆盖" :value="gapSummary.by_type?.weak || 0" />
            <n-statistic label="可超越" :value="gapSummary.by_type?.beatable || 0" />
            <n-statistic label="平均机会分" :value="gapSummary.avg_opportunity || 0" />
          </n-space>
          <n-data-table
            :columns="gapColumns"
            :data="gaps"
            :bordered="false"
            size="small"
            :pagination="{ pageSize: 10 }"
          />
        </n-card>
      </n-gi>
    </n-grid>

    <n-card v-if="strategy.brand" title="差异化策略建议">
      <n-descriptions :column="2" label-placement="left" bordered size="small">
        <n-descriptions-item label="品牌">{{ strategy.brand }}</n-descriptions-item>
        <n-descriptions-item label="竞品数">{{ strategy.competitor_count }}</n-descriptions-item>
        <n-descriptions-item label="总缺口">{{ strategy.total_gaps }}</n-descriptions-item>
        <n-descriptions-item label="未覆盖缺口">{{ strategy.uncovered_gaps }}</n-descriptions-item>
      </n-descriptions>

      <n-card title="重点发力方向" size="small" style="margin-top: 12px" v-if="strategy.recommended_focus?.length">
        <n-list bordered size="small">
          <n-list-item v-for="(item, idx) in strategy.recommended_focus" :key="idx">
            {{ item }}
          </n-list-item>
        </n-list>
      </n-card>

      <n-card title="差异化角度" size="small" style="margin-top: 12px" v-if="strategy.differentiation_angles?.length">
        <n-list bordered size="small">
          <n-list-item v-for="(angle, idx) in strategy.differentiation_angles" :key="idx">
            {{ angle }}
          </n-list-item>
        </n-list>
      </n-card>

      <n-card title="高机会关键词" size="small" style="margin-top: 12px" v-if="strategy.top_opportunities?.length">
        <n-data-table
          :columns="gapColumns"
          :data="strategy.top_opportunities"
          :bordered="false"
          size="small"
        />
      </n-card>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { h, ref } from 'vue'
import { NTag, useMessage, type DataTableColumns } from 'naive-ui'
import request from '@/api/request'

const message = useMessage()

const competitorInput = ref('')
const keywordInput = ref('')
const loadingAnalysis = ref(false)
const loadingStrategy = ref(false)
const profiles = ref<any[]>([])
const gaps = ref<any[]>([])
const gapSummary = ref<Record<string, any>>({})
const strategy = ref<Record<string, any>>({})

const profileColumns: DataTableColumns<any> = [
  { title: '竞品', key: 'name', width: 120 },
  { title: '覆盖平台', key: 'platforms', render: (row: any) => (row.platforms || []).join('、') },
  { title: '内容主题', key: 'content_themes', render: (row: any) => (row.content_themes || []).join('、'), ellipsis: { tooltip: true } },
  { title: '发布频率', key: 'posting_frequency', width: 100 },
  {
    title: 'GEO 均分',
    key: 'avg_geo_score',
    width: 100,
    sorter: (a: any, b: any) => a.avg_geo_score - b.avg_geo_score,
    render: (row: any) => h(NTag, { type: row.avg_geo_score > 60 ? 'success' : row.avg_geo_score > 40 ? 'warning' : 'error', size: 'small' }, () => `${row.avg_geo_score}`),
  },
  { title: '优势', key: 'strengths', render: (row: any) => (row.strengths || []).join('、'), ellipsis: { tooltip: true } },
  { title: '弱点', key: 'weaknesses', render: (row: any) => (row.weaknesses || []).join('、'), ellipsis: { tooltip: true } },
]

const gapColumns: DataTableColumns<any> = [
  { title: '关键词', key: 'keyword', width: 120 },
  {
    title: '缺口类型',
    key: 'gap_type_label',
    width: 90,
    render: (row: any) => {
      const typeMap: Record<string, string> = { uncovered: 'error', weak: 'warning', beatable: 'success' }
      return h(NTag, { type: (typeMap[row.gap_type] || 'default') as any, size: 'small' }, () => row.gap_type_label || row.gap_type)
    },
  },
  { title: '平台', key: 'platform', width: 90 },
  { title: '竞品覆盖数', key: 'competitor_count', width: 100 },
  {
    title: '机会分',
    key: 'opportunity_score',
    width: 80,
    sorter: (a: any, b: any) => a.opportunity_score - b.opportunity_score,
  },
  { title: '建议行动', key: 'recommended_action', ellipsis: { tooltip: true } },
]

function parseInput(input: string): string[] {
  return input.split(/[,，]/).map(s => s.trim()).filter(Boolean)
}

async function runAnalysis() {
  const competitors = parseInput(competitorInput.value)
  const keywords = parseInput(keywordInput.value)
  if (!competitors.length) {
    message.warning('请输入竞品名称')
    return
  }
  if (!keywords.length) {
    message.warning('请输入关键词')
    return
  }

  loadingAnalysis.value = true
  try {
    const [profileRes, gapRes] = await Promise.all([
      request.post<{ profiles: any[] }>('/competitors/analyze', { competitor_names: competitors, keywords }),
      request.post<{ gaps: any[]; summary: any }>('/competitors/gaps', { keywords, competitor_names: competitors }),
    ])
    profiles.value = profileRes.profiles || []
    gaps.value = gapRes.gaps || []
    gapSummary.value = gapRes.summary || {}
    message.success(`分析完成：${profiles.value.length} 个竞品，${gaps.value.length} 个缺口`)
  } catch {
    message.error('竞品分析失败')
  } finally {
    loadingAnalysis.value = false
  }
}

async function genStrategy() {
  const competitors = parseInput(competitorInput.value)
  const keywords = parseInput(keywordInput.value)

  loadingStrategy.value = true
  try {
    const res = await request.post<Record<string, any>>('/competitors/strategy', {
      brand_name: '我方品牌',
      competitor_names: competitors,
      keywords,
    })
    strategy.value = res
    message.success('差异化策略生成完成')
  } catch {
    message.error('策略生成失败')
  } finally {
    loadingStrategy.value = false
  }
}
</script>
