<template>
  <n-space vertical :size="18">
    <n-card title="内容日历" :bordered="false">
      <n-space align="center" :wrap="true">
        <n-input
          v-model:value="topic"
          placeholder="输入研究主题"
          style="width: 280px"
          clearable
        />
        <n-input
          v-model:value="brandName"
          placeholder="品牌名称（可选）"
          style="width: 160px"
          clearable
        />
        <n-input
          v-model:value="industry"
          placeholder="行业（可选）"
          style="width: 160px"
          clearable
        />
        <n-input-number
          v-model:value="weeks"
          :min="1"
          :max="12"
          placeholder="周数"
          style="width: 100px"
        />
        <n-button type="primary" :loading="loading" :disabled="!topic" @click="generate">
          生成日历
        </n-button>
      </n-space>
    </n-card>

    <template v-if="calendar">
      <!-- Summary -->
      <n-card :bordered="false">
        <n-space vertical>
          <n-text>共规划 <n-text strong>{{ calendar.entries.length }}</n-text> 篇内容</n-text>
          <n-space>
            <n-tag type="error">P0: {{ p0Count }}</n-tag>
            <n-tag type="warning">P1: {{ p1Count }}</n-tag>
            <n-tag type="info">P2: {{ p2Count }}</n-tag>
          </n-space>
        </n-space>
      </n-card>

      <!-- Calendar Table -->
      <n-card :bordered="false">
        <n-tabs type="segment" v-model:value="viewMode">
          <n-tab-pane name="table" tab="列表视图">
            <n-data-table :columns="calendarColumns" :data="calendar.entries" :bordered="false" size="small" />
          </n-tab-pane>
          <n-tab-pane name="week" tab="周视图">
            <n-grid :cols="weeks" :x-gap="12">
              <n-grid-item v-for="w in weeks" :key="w">
                <n-card :title="`第 ${w} 周`" size="small">
                  <n-space vertical :size="6">
                    <n-card
                      v-for="(entry, i) in entriesByWeek(w)"
                      :key="i"
                      size="small"
                      :style="{ borderLeft: `3px solid ${priorityColor(entry.priority)}` }"
                    >
                      <n-text strong>{{ entry.content_topic }}</n-text>
                      <n-space :size="4" style="margin-top: 4px">
                        <n-tag size="tiny" :type="priorityType(entry.priority)">{{ entry.priority }}</n-tag>
                        <n-tag size="tiny">{{ platformName(entry.target_platform) }}</n-tag>
                        <n-tag size="tiny" :bordered="false">{{ entry.content_type }}</n-tag>
                      </n-space>
                    </n-card>
                    <n-text v-if="!entriesByWeek(w).length" depth="3">暂无内容</n-text>
                  </n-space>
                </n-card>
              </n-grid-item>
            </n-grid>
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </template>

    <n-alert v-if="error" type="error" closable @close="error = ''">{{ error }}</n-alert>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { NTag } from 'naive-ui'
import { keywordResearchApi } from '@/api/contentCalendar'
import type { ContentCalendarResult, CalendarEntry } from '@/api/contentCalendar'

const topic = ref('')
const brandName = ref('')
const industry = ref('')
const weeks = ref(4)
const loading = ref(false)
const error = ref('')
const calendar = ref<ContentCalendarResult | null>(null)
const viewMode = ref('table')

const p0Count = computed(() => calendar.value?.entries.filter(e => e.priority === 'P0').length || 0)
const p1Count = computed(() => calendar.value?.entries.filter(e => e.priority === 'P1').length || 0)
const p2Count = computed(() => calendar.value?.entries.filter(e => e.priority === 'P2').length || 0)

const platformNames: Record<string, string> = {
  wechat: '公众号',
  xiaohongshu: '小红书',
  zhihu: '知乎',
  video: '短视频'
}

const platformName = (p: string) => platformNames[p] || p
const priorityType = (p: string) => (p === 'P0' ? 'error' : p === 'P1' ? 'warning' : 'info')
const priorityColor = (p: string) => (p === 'P0' ? '#e03050' : p === 'P1' ? '#f0a020' : '#2080f0')

function entriesByWeek(w: number): CalendarEntry[] {
  return calendar.value?.entries.filter(e => e.suggested_week === w) || []
}

const calendarColumns = [
  {
    title: '优先级',
    key: 'priority',
    width: 80,
    render: (row: any) => h(NTag, { type: priorityType(row.priority), size: 'small' }, () => row.priority)
  },
  { title: '周次', key: 'suggested_week', width: 60 },
  { title: '内容主题', key: 'content_topic' },
  { title: '内容类型', key: 'content_type', width: 100 },
  {
    title: '平台',
    key: 'target_platform',
    width: 80,
    render: (row: any) => platformName(row.target_platform)
  },
  {
    title: '关键词',
    key: 'target_keywords',
    render: (row: any) => row.target_keywords?.join('、') || ''
  },
  { title: '概要', key: 'brief' }
]

async function generate() {
  if (!topic.value) return
  loading.value = true
  error.value = ''
  calendar.value = null
  try {
    calendar.value = await keywordResearchApi.generateCalendar(
      topic.value,
      [],
      brandName.value || undefined,
      industry.value || undefined,
      weeks.value
    )
  } catch (e: any) {
    error.value = e.message || '生成失败'
  } finally {
    loading.value = false
  }
}
</script>
