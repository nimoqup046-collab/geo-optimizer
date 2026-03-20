<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <n-alert type="info" :show-icon="false">
      {{ UI_TEXT.distribution.modeNotice }}
    </n-alert>

    <n-card title="演示辅助" :bordered="false">
      <n-space>
        <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
        <n-button type="primary" :loading="seeding" @click="seedDemoData">
          {{ UI_TEXT.demo.bootstrap }}
        </n-button>
      </n-space>
    </n-card>

    <n-card :title="UI_TEXT.distribution.createTitle" :bordered="false">
      <n-form inline :model="taskForm">
        <n-form-item label="品牌">
          <n-select v-model:value="taskForm.brand_id" :options="brandOptions" style="width: 220px" />
        </n-form-item>
        <n-form-item label="内容变体">
          <n-select
            v-model:value="taskForm.content_variant_id"
            :options="variantOptions"
            style="width: 420px"
          />
        </n-form-item>
        <n-form-item label="平台">
          <n-input v-model:value="taskForm.platform" style="width: 140px" />
        </n-form-item>
        <n-form-item label="排期时间">
          <n-date-picker
            v-model:value="scheduledAtValue"
            type="datetime"
            clearable
            style="width: 220px"
          />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" @click="createTask">{{ UI_TEXT.distribution.createTask }}</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <n-card :title="UI_TEXT.distribution.queueTitle" :bordered="false">
      <n-data-table :columns="taskColumns" :data="tasks" />
      <n-empty v-if="tasks.length === 0" description="暂无发布任务" />
    </n-card>

    <n-card :title="UI_TEXT.distribution.performanceTitle" :bordered="false">
      <n-form :model="perfForm">
        <n-form-item label="关键词">
          <n-input v-model:value="perfForm.keyword" />
        </n-form-item>
        <n-form-item label="平台">
          <n-input v-model:value="perfForm.platform" />
        </n-form-item>
        <n-form-item label="阅读 / 点赞 / 评论 / 线索">
          <n-space>
            <n-input-number v-model:value="perfForm.reads" />
            <n-input-number v-model:value="perfForm.likes" />
            <n-input-number v-model:value="perfForm.comments" />
            <n-input-number v-model:value="perfForm.leads" />
          </n-space>
        </n-form-item>
      </n-form>
      <n-space>
        <n-button @click="importPerformance">{{ UI_TEXT.distribution.savePerformance }}</n-button>
        <n-button type="primary" @click="runInsights">{{ UI_TEXT.distribution.runInsights }}</n-button>
      </n-space>
    </n-card>

    <n-card :title="UI_TEXT.distribution.insightsTitle" :bordered="false">
      <n-list bordered>
        <n-list-item v-for="insight in insights" :key="insight.id">
          <n-thing :title="insight.title">
            <template #description>{{ insight.details }}</template>
            <template #footer>
              <n-space>
                <n-tag v-for="(item, idx) in insight.action_items" :key="idx">{{ item }}</n-tag>
              </n-space>
            </template>
          </n-thing>
        </n-list-item>
      </n-list>
      <n-empty v-if="insights.length === 0" description="暂无优化建议" />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import {
  brandApi,
  contentApi,
  optimizationApi,
  performanceApi,
  publishApi,
  type ContentItem,
  type PublishTask
} from '@/api'
import { UI_TEXT } from '@/constants/uiText'
import { runDemoSeed } from '@/services/demoSeed'

const message = useMessage()
const loading = ref(false)
const seeding = ref(false)
const loadError = ref('')
const brands = ref<any[]>([])
const contents = ref<ContentItem[]>([])
const tasks = ref<PublishTask[]>([])
const insights = ref<any[]>([])

const scheduledAtValue = ref<number | null>(null)

const taskForm = reactive({
  brand_id: '',
  content_variant_id: '',
  platform: 'wechat'
})

const perfForm = reactive({
  keyword: '',
  platform: 'wechat',
  reads: 0,
  likes: 0,
  comments: 0,
  leads: 0
})

const brandOptions = computed(() =>
  brands.value.map((brand) => ({ label: brand.name, value: brand.id }))
)

const variantOptions = computed(() => {
  const options: { label: string; value: string }[] = []
  for (const item of contents.value) {
    for (const variant of item.variants) {
      options.push({
        label: `${item.topic} | ${variant.platform} | ${variant.title}`,
        value: variant.id
      })
    }
  }
  return options
})

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    brands.value = await brandApi.list()
    if (!taskForm.brand_id && brands.value.length > 0) taskForm.brand_id = brands.value[0].id
    contents.value = await contentApi.list(taskForm.brand_id ? { brand_id: taskForm.brand_id } : undefined)
    tasks.value = await publishApi.list(taskForm.brand_id ? { brand_id: taskForm.brand_id } : undefined)
    insights.value = await optimizationApi.list(taskForm.brand_id ? { brand_id: taskForm.brand_id } : undefined)
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

watch(
  () => taskForm.brand_id,
  async (next, prev) => {
    if (next !== prev) await load()
  }
)

const createTask = async () => {
  if (!taskForm.brand_id || !taskForm.content_variant_id) {
    message.warning('请先选择品牌和内容变体')
    return
  }
  await publishApi.create({
    ...taskForm,
    scheduled_at: scheduledAtValue.value ? new Date(scheduledAtValue.value).toISOString() : null
  })
  message.success('发布任务已创建')
  await load()
}

const importPerformance = async () => {
  if (!taskForm.brand_id) {
    message.warning('请先选择品牌')
    return
  }
  await performanceApi.importData({
    brand_id: taskForm.brand_id,
    entries: [
      {
        keyword: perfForm.keyword || '婚姻修复',
        platform: perfForm.platform,
        reads: perfForm.reads,
        likes: perfForm.likes,
        comments: perfForm.comments,
        leads: perfForm.leads
      }
    ]
  })
  message.success('表现数据已保存')
}

const runInsights = async () => {
  if (!taskForm.brand_id) {
    message.warning('请先选择品牌')
    return
  }
  await optimizationApi.run({ brand_id: taskForm.brand_id, lookback_days: 30 })
  insights.value = await optimizationApi.list({ brand_id: taskForm.brand_id })
  message.success('优化建议已更新')
}

const seedDemoData = async () => {
  seeding.value = true
  try {
    await runDemoSeed(false)
    message.success('演示数据已生成')
    await load()
  } catch (error: any) {
    message.error(`演示生成失败：${error?.message || UI_TEXT.common.unknownError}`)
  } finally {
    seeding.value = false
  }
}

const markPosted = async (row: PublishTask) => {
  await publishApi.update(row.id, {
    status: 'posted',
    human_confirmation: 'confirmed',
    publish_url: row.publish_url || 'https://example.com/demo-post'
  })
  message.success('任务已标记为已发布')
  await load()
}

const taskColumns = [
  { title: '平台', key: 'platform' },
  { title: '状态', key: 'status' },
  { title: '人工确认', key: 'human_confirmation' },
  {
    title: '排期时间',
    key: 'scheduled_at',
    render: (row: PublishTask) => (row.scheduled_at ? new Date(row.scheduled_at).toLocaleString() : '-')
  },
  {
    title: '发布链接',
    key: 'publish_url',
    render: (row: PublishTask) => row.publish_url || '-'
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: PublishTask) =>
      h(
        NButton,
        { size: 'small', onClick: () => markPosted(row) },
        { default: () => UI_TEXT.distribution.markPosted }
      )
  }
]

onMounted(load)
</script>
