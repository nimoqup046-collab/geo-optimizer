<template>
  <n-space vertical :size="16">
    <n-card title="AI 搜索排名监控">
      <n-alert type="info" title="功能说明" style="margin-bottom: 12px">
        追踪内容在 ChatGPT、Perplexity、Bing Copilot 等 AI 搜索引擎中的排名，
        验证 GEO 优化效果，发现优化机会。
      </n-alert>

      <n-space vertical :size="12">
        <n-input-group>
          <n-input
            v-model:value="keywordInput"
            placeholder="输入关键词（多个用逗号分隔）"
            @keyup.enter="checkRankings"
          />
          <n-select
            v-model:value="platform"
            :options="platformOptions"
            style="width: 140px"
          />
          <n-input-number v-model:value="geoScore" :min="0" :max="100" placeholder="GEO评分" style="width: 120px" />
          <n-button type="primary" :loading="loadingCheck" @click="checkRankings">检查排名</n-button>
        </n-input-group>
      </n-space>
    </n-card>

    <n-card v-if="rankingResults.length" title="排名检查结果">
      <n-data-table
        :columns="rankColumns"
        :data="rankingResults"
        :bordered="false"
        size="small"
      />
    </n-card>

    <n-grid v-if="rankingResults.length" :cols="2" :x-gap="12" :y-gap="12">
      <n-gi>
        <n-card title="排名趋势" size="small">
          <n-spin :show="loadingTrends">
            <div v-if="trends.engines">
              <n-descriptions :column="1" label-placement="left" bordered size="small">
                <n-descriptions-item label="整体趋势">
                  <n-tag :type="trends.trend === 'improving' ? 'success' : 'warning'" size="small">
                    {{ trendLabels[trends.trend] || trends.trend }}
                  </n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="平均排名">{{ trends.avg_position || '-' }}</n-descriptions-item>
                <n-descriptions-item label="数据点数">{{ trends.data_points || 0 }}</n-descriptions-item>
              </n-descriptions>
              <n-table :bordered="false" :single-line="false" size="small" style="margin-top: 8px">
                <thead>
                  <tr>
                    <th>AI 引擎</th>
                    <th>趋势</th>
                    <th>最新排名</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(data, engine) in trends.engines" :key="engine">
                    <td>{{ engineLabels[engine as string] || engine }}</td>
                    <td>
                      <n-tag :type="data.trend === 'improving' ? 'success' : data.trend === 'declining' ? 'error' : 'default'" size="small">
                        {{ trendLabels[data.trend] || data.trend }}
                      </n-tag>
                    </td>
                    <td>{{ data.latest || '-' }}</td>
                  </tr>
                </tbody>
              </n-table>
            </div>
            <n-empty v-else description="暂无趋势数据" />
          </n-spin>
        </n-card>
      </n-gi>

      <n-gi>
        <n-card title="优化建议" size="small">
          <n-spin :show="loadingActions">
            <n-list v-if="actions.length" bordered size="small">
              <n-list-item v-for="(action, idx) in actions" :key="idx">
                <n-thing>
                  <template #header>
                    <n-space align="center" :size="4">
                      <n-tag :type="action.priority === 'high' ? 'error' : action.priority === 'medium' ? 'warning' : 'default'" size="small">
                        {{ action.priority === 'high' ? '高优' : action.priority === 'medium' ? '中优' : '低优' }}
                      </n-tag>
                      <span>{{ action.keyword }}</span>
                    </n-space>
                  </template>
                  <template #description>
                    <div>{{ action.description }}</div>
                    <n-text depth="3" style="font-size: 12px">预期效果：{{ action.expected_impact }}</n-text>
                  </template>
                </n-thing>
              </n-list-item>
            </n-list>
            <n-empty v-else description="暂无优化建议" />
          </n-spin>
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
</template>

<script setup lang="ts">
import { h, ref } from 'vue'
import { NTag, useMessage, type DataTableColumns } from 'naive-ui'
import request from '@/api/request'

const message = useMessage()

const keywordInput = ref('')
const platform = ref('wechat')
const geoScore = ref(50)
const loadingCheck = ref(false)
const loadingTrends = ref(false)
const loadingActions = ref(false)
const rankingResults = ref<any[]>([])
const trends = ref<Record<string, any>>({})
const actions = ref<any[]>([])

const platformOptions = [
  { label: '公众号', value: 'wechat' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '知乎', value: 'zhihu' },
  { label: '短视频', value: 'video' },
]

const engineLabels: Record<string, string> = {
  chatgpt: 'ChatGPT',
  perplexity: 'Perplexity',
  bing_copilot: 'Bing Copilot',
}

const trendLabels: Record<string, string> = {
  improving: '上升',
  declining: '下降',
  stable: '稳定',
  needs_work: '待提升',
  no_data: '无数据',
  insufficient_data: '数据不足',
}

const rankColumns: DataTableColumns<any> = [
  { title: '关键词', key: 'keyword', width: 140 },
  {
    title: 'AI 引擎',
    key: 'ai_engine',
    width: 120,
    render: (row: any) => engineLabels[row.ai_engine] || row.ai_engine,
  },
  {
    title: '排名',
    key: 'rank_position',
    width: 80,
    sorter: (a: any, b: any) => a.rank_position - b.rank_position,
    render: (row: any) => {
      if (row.rank_position === 0) return h(NTag, { type: 'error', size: 'small' }, () => '未收录')
      const type = row.rank_position <= 3 ? 'success' : row.rank_position <= 10 ? 'warning' : 'default'
      return h(NTag, { type, size: 'small' }, () => `#${row.rank_position}`)
    },
  },
  {
    title: '片段收录',
    key: 'snippet_found',
    width: 90,
    render: (row: any) => h(NTag, { type: row.snippet_found ? 'success' : 'default', size: 'small' }, () => row.snippet_found ? '是' : '否'),
  },
  {
    title: '品牌提及',
    key: 'brand_mentioned',
    width: 90,
    render: (row: any) => h(NTag, { type: row.brand_mentioned ? 'success' : 'default', size: 'small' }, () => row.brand_mentioned ? '是' : '否'),
  },
]

async function checkRankings() {
  const keywords = keywordInput.value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
  if (!keywords.length) {
    message.warning('请输入关键词')
    return
  }

  loadingCheck.value = true
  try {
    const res = await request.post<{ results: any[] }>('/ranking/check', {
      keywords,
      platform: platform.value,
      geo_score: geoScore.value,
    })
    rankingResults.value = res.results || []
    message.success(`检查完成，共 ${rankingResults.value.length} 条结果`)

    // Fetch trends and actions in parallel.
    fetchTrends(keywords[0])
    fetchActions(keywords[0])
  } catch {
    message.error('排名检查失败')
  } finally {
    loadingCheck.value = false
  }
}

async function fetchTrends(keyword: string) {
  loadingTrends.value = true
  try {
    const res = await request.get<{ trends: any }>('/ranking/trends', { params: { keyword } })
    trends.value = res.trends || {}
  } catch {
    // Silent fail for trends.
  } finally {
    loadingTrends.value = false
  }
}

async function fetchActions(keyword: string) {
  loadingActions.value = true
  try {
    const firstResult = rankingResults.value.find((r: any) => r.keyword === keyword)
    const res = await request.get<{ actions: any[] }>('/ranking/actions', {
      params: {
        keyword,
        rank_position: firstResult?.rank_position || 0,
        geo_score: geoScore.value,
      },
    })
    actions.value = res.actions || []
  } catch {
    // Silent fail for actions.
  } finally {
    loadingActions.value = false
  }
}
</script>
