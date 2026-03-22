<template>
  <n-space vertical :size="16">
    <n-card title="数据源管理">
      <n-space vertical :size="12">
        <n-alert type="info" title="数据源说明">
          通过外部数据源获取关键词搜索量、趋势和竞争度，让分析从静态规则升级为数据驱动。
          当前使用模拟数据源，配置 API Key 后可切换为真实数据。
        </n-alert>

        <n-card title="可用数据源" size="small">
          <n-spin :show="loadingProviders">
            <n-table :bordered="false" :single-line="false">
              <thead>
                <tr>
                  <th>数据源</th>
                  <th>状态</th>
                  <th>需要 API Key</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in providers" :key="p.name">
                  <td>{{ p.display_name }}</td>
                  <td>
                    <n-tag :type="p.name === 'mock' ? 'success' : 'warning'" size="small">
                      {{ p.name === 'mock' ? '可用' : '待配置' }}
                    </n-tag>
                  </td>
                  <td>{{ p.requires_key ? '是' : '否' }}</td>
                </tr>
              </tbody>
            </n-table>
          </n-spin>
        </n-card>
      </n-space>
    </n-card>

    <n-card title="关键词数据查询">
      <n-space vertical :size="12">
        <n-input-group>
          <n-input
            v-model:value="keywordInput"
            placeholder="输入关键词（多个用逗号分隔）"
            @keyup.enter="fetchData"
          />
          <n-button type="primary" :loading="loadingFetch" @click="fetchData">查询数据</n-button>
        </n-input-group>

        <n-data-table
          v-if="metrics.length"
          :columns="columns"
          :data="metrics"
          :bordered="false"
          size="small"
        />

        <n-card v-if="summary.total_keywords" title="汇总统计" size="small">
          <n-space>
            <n-statistic label="平均搜索量" :value="summary.avg_search_volume" />
            <n-statistic label="平均竞争度" :value="summary.avg_competition" />
            <n-statistic label="平均AI潜力" :value="summary.avg_ai_potential" />
            <n-statistic label="高搜索量词" :value="(summary.high_volume_keywords || []).length" />
          </n-space>
        </n-card>
      </n-space>
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NTag, useMessage, type DataTableColumns } from 'naive-ui'
import request from '@/api/request'

const message = useMessage()

const providers = ref<any[]>([])
const loadingProviders = ref(false)
const keywordInput = ref('')
const loadingFetch = ref(false)
const metrics = ref<any[]>([])
const summary = ref<Record<string, any>>({})

const columns: DataTableColumns<any> = [
  { title: '关键词', key: 'keyword', width: 160 },
  { title: '搜索量', key: 'search_volume', width: 100, sorter: (a: any, b: any) => a.search_volume - b.search_volume },
  {
    title: '趋势指数',
    key: 'trend_index',
    width: 100,
    render: (row: any) => h(NTag, { type: row.trend_index > 60 ? 'success' : row.trend_index > 30 ? 'warning' : 'default', size: 'small' }, () => `${row.trend_index}`)
  },
  {
    title: '竞争度',
    key: 'competition_score',
    width: 100,
    render: (row: any) => h(NTag, { type: row.competition_score > 70 ? 'error' : row.competition_score > 40 ? 'warning' : 'success', size: 'small' }, () => `${row.competition_score}`)
  },
  {
    title: 'AI引用潜力',
    key: 'ai_citation_potential',
    width: 110,
    render: (row: any) => h(NTag, { type: row.ai_citation_potential > 70 ? 'success' : 'default', size: 'small' }, () => `${row.ai_citation_potential}`)
  },
  { title: '相关词', key: 'related_keywords', render: (row: any) => (row.related_keywords || []).join('、') },
  { title: '数据源', key: 'source', width: 80 },
]

onMounted(async () => {
  loadingProviders.value = true
  try {
    const res = await request.get<{ providers: any[] }>('/data-sources/providers')
    providers.value = res.providers || []
  } catch {
    message.error('获取数据源列表失败')
  } finally {
    loadingProviders.value = false
  }
})

async function fetchData() {
  const keywords = keywordInput.value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
  if (!keywords.length) {
    message.warning('请输入关键词')
    return
  }
  loadingFetch.value = true
  try {
    const res = await request.post<{ enriched: any[]; summary: any }>('/data-sources/enrich-analysis', { keywords })
    metrics.value = res.enriched || []
    summary.value = res.summary || {}
    message.success(`查询完成，共 ${metrics.value.length} 个关键词`)
  } catch {
    message.error('数据查询失败')
  } finally {
    loadingFetch.value = false
  }
}
</script>
