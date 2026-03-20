<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <n-card :title="UI_TEXT.brands.title" :bordered="false">
      <n-space>
        <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
      </n-space>
    </n-card>

    <n-card :bordered="false">
      <n-form inline :model="form">
        <n-form-item label="品牌名称">
          <n-input v-model:value="form.name" placeholder="请输入品牌名称" />
        </n-form-item>
        <n-form-item label="行业">
          <n-input v-model:value="form.industry" placeholder="emotion_consulting" />
        </n-form-item>
        <n-form-item label="语气">
          <n-input v-model:value="form.tone_of_voice" placeholder="专业、温和、可执行" />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" @click="createBrand">{{ UI_TEXT.brands.create }}</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <n-data-table :columns="columns" :data="brands" :bordered="false" />
  </n-space>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { brandApi, type BrandProfile } from '@/api'
import { UI_TEXT } from '@/constants/uiText'

const message = useMessage()
const brands = ref<BrandProfile[]>([])
const loading = ref(false)
const loadError = ref('')

const form = reactive({
  name: '',
  industry: 'emotion_consulting',
  tone_of_voice: '专业、温和、可执行',
  service_description: '情感与关系修复咨询服务',
  target_audience: '处于关系冲突中的成年人群',
  call_to_action: '提交你的具体情况，获取下一步建议',
  region: '上海 / 华东',
  competitors: [] as string[],
  banned_words: ['保证结果', '绝对成功'],
  glossary: { GEO: 'Generative Engine Optimization' },
  platform_preferences: { wechat: true, xiaohongshu: true, zhihu: true },
  content_boundaries: '不做医疗诊断，不做夸大承诺。'
})

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    brands.value = await brandApi.list()
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

const createBrand = async () => {
  if (!form.name.trim()) {
    message.warning('请先输入品牌名称')
    return
  }
  try {
    await brandApi.create(form)
    message.success('品牌已创建')
    form.name = ''
    await load()
  } catch (error: any) {
    message.error(`创建失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const columns = [
  { title: UI_TEXT.brands.table.brand, key: 'name' },
  { title: UI_TEXT.brands.table.industry, key: 'industry' },
  { title: UI_TEXT.brands.table.tone, key: 'tone_of_voice' },
  { title: UI_TEXT.brands.table.region, key: 'region' },
  {
    title: UI_TEXT.brands.table.action,
    key: 'actions',
    render: (row: BrandProfile) =>
      h(
        NButton,
        {
          size: 'small',
          onClick: async () => {
            try {
              await brandApi.update(row.id, {
                tone_of_voice: row.tone_of_voice || '专业、务实'
              })
              message.success('品牌已保存')
              await load()
            } catch (error: any) {
              message.error(`保存失败：${error?.message || UI_TEXT.common.unknownError}`)
            }
          }
        },
        { default: () => UI_TEXT.brands.quickSave }
      )
  }
]

onMounted(load)
</script>
