<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <n-card :title="UI_TEXT.workshop.generateTitle" :bordered="false">
      <n-form inline :model="generateForm">
        <n-form-item label="报告">
          <n-select
            v-model:value="generateForm.report_id"
            :options="reportOptions"
            style="width: 420px"
            placeholder="请选择报告"
          />
        </n-form-item>
        <n-form-item label="数量">
          <n-input-number v-model:value="generateForm.count" :min="1" :max="5" />
        </n-form-item>
        <n-form-item label="平台">
          <n-select
            v-model:value="generateForm.target_platforms"
            :options="platformOptions"
            multiple
            style="width: 360px"
          />
        </n-form-item>
        <n-form-item label="提示词档案">
          <n-select
            v-model:value="generateForm.prompt_profile_id"
            :options="promptProfileOptions"
            clearable
            style="width: 240px"
            placeholder="可选"
          />
        </n-form-item>
        <n-form-item label="生成模式">
          <n-select
            v-model:value="generateForm.mode"
            :options="modeOptions"
            style="width: 200px"
          />
        </n-form-item>
        <n-form-item :label="UI_TEXT.workshop.contentModelLabel">
          <n-select
            v-model:value="generateForm.llm_provider"
            :options="contentModelOptions"
            clearable
            style="width: 220px"
            :placeholder="UI_TEXT.workshop.contentModelDefault"
          />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="generating" @click="generate">
            {{ generateForm.mode === 'expert' ? '专家协作生成' : UI_TEXT.workshop.generate }}
          </n-button>
        </n-form-item>
      </n-form>
      <n-space style="margin-top: 12px">
        <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
      </n-space>
    </n-card>

    <n-card :title="UI_TEXT.workshop.listTitle" :bordered="false">
      <n-data-table :columns="columns" :data="items" />
      <n-empty v-if="items.length === 0" description="暂无内容，请先生成报告。" />
    </n-card>

    <n-card :title="UI_TEXT.workshop.promptProfiles" :bordered="false">
      <n-form inline :model="promptProfileForm">
        <n-form-item label="名称">
          <n-input v-model:value="promptProfileForm.name" style="width: 180px" />
        </n-form-item>
        <n-form-item label="角色">
          <n-input v-model:value="promptProfileForm.role" style="width: 140px" />
        </n-form-item>
        <n-form-item label="平台">
          <n-input v-model:value="promptProfileForm.platform" style="width: 120px" />
        </n-form-item>
        <n-form-item label="行业">
          <n-input v-model:value="promptProfileForm.industry" style="width: 140px" />
        </n-form-item>
        <n-form-item>
          <n-button @click="createPromptProfile">保存档案</n-button>
        </n-form-item>
      </n-form>
      <n-data-table :columns="promptProfileColumns" :data="promptProfiles" style="margin-top: 8px" />
    </n-card>

    <n-card :title="UI_TEXT.workshop.workflowSteps" :bordered="false">
      <n-form inline :model="workflowForm">
        <n-form-item label="名称">
          <n-input v-model:value="workflowForm.name" style="width: 220px" />
        </n-form-item>
        <n-form-item label="类型">
          <n-input v-model:value="workflowForm.step_type" style="width: 120px" />
        </n-form-item>
        <n-form-item label="适配器">
          <n-input v-model:value="workflowForm.adapter" style="width: 120px" />
        </n-form-item>
        <n-form-item>
          <n-button @click="createWorkflowStep">创建步骤</n-button>
        </n-form-item>
      </n-form>
      <n-data-table :columns="workflowColumns" :data="workflowSteps" style="margin-top: 8px" />
    </n-card>

    <n-modal v-model:show="showWechatPreview" preset="card" title="公众号图文预览" style="width: 760px; max-height: 90vh;">
      <n-space vertical :size="12">
        <n-space>
          <n-button type="primary" size="small" @click="downloadWechatHtml">下载 HTML</n-button>
          <n-button size="small" @click="showWechatPreview = false">关闭</n-button>
        </n-space>
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; overflow: auto; max-height: 70vh;">
          <iframe
            v-if="wechatPreviewHtml"
            :srcdoc="wechatPreviewHtml"
            style="width: 100%; height: 600px; border: none;"
          />
        </div>
      </n-space>
    </n-modal>
  </n-space>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import {
  analysisApi,
  contentApi,
  creativeApi,
  exportApi,
  promptProfileApi,
  workflowStepApi,
  type AnalysisReport,
  type ContentItem,
  type PromptProfile,
  type WorkflowStep
} from '@/api'
import { UI_TEXT } from '@/constants/uiText'

const message = useMessage()
const generating = ref(false)
const loading = ref(false)
const loadError = ref('')
const reports = ref<AnalysisReport[]>([])
const items = ref<ContentItem[]>([])
const promptProfiles = ref<PromptProfile[]>([])
const workflowSteps = ref<WorkflowStep[]>([])

const featureWechatRichPost = true
const wechatGenerating = ref(false)
const wechatPreviewHtml = ref('')
const showWechatPreview = ref(false)

const platformOptions = [
  { label: '公众号', value: 'wechat' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '知乎', value: 'zhihu' },
  { label: '短视频脚本', value: 'video' }
]

const modeOptions = [
  { label: '标准生成', value: 'standard' },
  { label: '专家协作生成', value: 'expert' }
]

const contentModelOptions = [
  { label: UI_TEXT.workshop.contentModelClaude, value: 'openrouter' },
  { label: UI_TEXT.workshop.contentModelGemini, value: 'openrouter_gemini' }
]

const generateForm = reactive({
  report_id: '',
  count: 1,
  target_platforms: ['wechat', 'xiaohongshu', 'zhihu', 'video'],
  prompt_profile_id: null as string | null,
  mode: 'standard',
  llm_provider: null as string | null
})

const promptProfileForm = reactive({
  name: '情感咨询-主编模板',
  role: 'brand_editor',
  platform: 'wechat',
  industry: 'emotion_consulting'
})

const workflowForm = reactive({
  name: '内容优化-mock步骤',
  step_type: 'skill_step',
  adapter: 'mock'
})

const reportOptions = computed(() =>
  reports.value.map((report) => ({ label: report.title, value: report.report_id }))
)

const promptProfileOptions = computed(() =>
  promptProfiles.value.map((item) => ({ label: item.name, value: item.id }))
)

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
    const [reportList, contentList, profileList, workflowList] = await Promise.all([
      analysisApi.listReports(),
      contentApi.list(),
      promptProfileApi.list(),
      workflowStepApi.list()
    ])
    reports.value = reportList
    items.value = contentList
    promptProfiles.value = profileList
    workflowSteps.value = workflowList

    if (!generateForm.report_id && reports.value.length > 0) {
      generateForm.report_id = reports.value[0].report_id
    }
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

const generate = async () => {
  if (!generateForm.report_id) {
    message.warning('请先选择报告')
    return
  }
  generating.value = true
  try {
    await contentApi.generate({
      report_id: generateForm.report_id,
      content_type: 'article',
      target_platforms: generateForm.target_platforms,
      count: generateForm.count,
      prompt_profile_id: generateForm.prompt_profile_id || undefined,
      llm_provider: generateForm.llm_provider || undefined,
      mode: generateForm.mode
    })
    message.success('内容已生成')
    await load()
  } catch (error: any) {
    message.error(`生成失败：${error?.message || UI_TEXT.common.unknownError}`)
  } finally {
    generating.value = false
  }
}

const approveItem = async (row: ContentItem) => {
  await contentApi.updateStatus(row.id, { status: 'approved' })
  message.success('内容已审核通过')
  await load()
}

const exportItem = async (row: ContentItem, format: 'md' | 'pdf') => {
  const blob: Blob = await exportApi.export({ content_item_ids: [row.id], format })
  downloadBlob(blob, `content_${row.id}.${format}`)
}

const triggerWechatRichPost = async (row: ContentItem) => {
  wechatGenerating.value = true
  try {
    const wechatVariant = row.variants.find((item) => item.platform === 'wechat')
    const result = await creativeApi.createWechatRichPost({
      content_item_id: row.id,
      variant_id: wechatVariant?.id
    })
    message.success(result.message)
    // Show HTML preview if available
    if (result.payload?.html) {
      wechatPreviewHtml.value = result.payload.html
      showWechatPreview.value = true
    }
  } catch (error: any) {
    message.error(`图文生成失败：${error?.message || UI_TEXT.common.unknownError}`)
  } finally {
    wechatGenerating.value = false
  }
}

const downloadWechatHtml = () => {
  if (!wechatPreviewHtml.value) return
  const blob = new Blob([wechatPreviewHtml.value], { type: 'text/html;charset=utf-8' })
  downloadBlob(blob, `wechat_article_${Date.now()}.html`)
}

const createPromptProfile = async () => {
  try {
    await promptProfileApi.create({
      ...promptProfileForm,
      is_default: true,
      tone_of_voice: '专业、温和、可执行',
      banned_words: ['绝对化承诺', '保证结果'],
      call_to_action: '引导用户提交具体场景',
      system_prompt:
        '你是情感咨询内容团队的高级编辑，输出必须结构清晰、可执行、可复用。',
      user_prompt_template:
        '请围绕主题 {topic} 生成 {platform} 内容。品牌：{brand_name}，语气：{tone_of_voice}，CTA：{call_to_action}，禁用词：{banned_words}。'
    })
    message.success('提示词档案已保存')
    await load()
  } catch (error: any) {
    message.error(`保存失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const createWorkflowStep = async () => {
  try {
    await workflowStepApi.create({
      ...workflowForm,
      status: 'idle',
      retry_limit: 2,
      input_payload: {
        objective: '优化现有内容',
        provider: 'mock'
      },
      config: {
        note: '下一轮替换为真实 skill 适配器'
      }
    })
    message.success('编排步骤已创建')
    await load()
  } catch (error: any) {
    message.error(`创建失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const runWorkflowStep = async (row: WorkflowStep) => {
  try {
    await workflowStepApi.run(row.id, {
      payload: {
        trigger: 'manual',
        at: new Date().toISOString()
      }
    })
    message.success('编排步骤已执行（mock）')
    await load()
  } catch (error: any) {
    message.error(`执行失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const columns = [
  { title: '主题', key: 'topic' },
  { title: '类型', key: 'content_type' },
  { title: '状态', key: 'status' },
  {
    title: '变体数',
    key: 'variants',
    render: (row: ContentItem) => row.variants.length
  },
  {
    title: '更新时间',
    key: 'updated_at',
    render: (row: ContentItem) => new Date(row.updated_at).toLocaleString()
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: ContentItem) =>
      h('div', { style: 'display:flex;gap:8px;flex-wrap:wrap;' }, [
        h(
          NButton,
          { size: 'small', onClick: () => approveItem(row) },
          { default: () => UI_TEXT.workshop.approve }
        ),
        h(
          NButton,
          { size: 'small', onClick: () => exportItem(row, 'md') },
          { default: () => UI_TEXT.workshop.exportMd }
        ),
        h(
          NButton,
          { size: 'small', onClick: () => exportItem(row, 'pdf') },
          { default: () => UI_TEXT.workshop.exportPdf }
        ),
        h(
          NButton,
          { size: 'small', loading: wechatGenerating.value, onClick: () => triggerWechatRichPost(row) },
          { default: () => UI_TEXT.workshop.wechatRichPost }
        )
      ])
  }
]

const promptProfileColumns = [
  { title: '名称', key: 'name' },
  { title: '角色', key: 'role' },
  { title: '平台', key: 'platform' },
  { title: '行业', key: 'industry' },
  {
    title: '默认',
    key: 'is_default',
    render: (row: PromptProfile) => (row.is_default ? '是' : '否')
  }
]

const workflowColumns = [
  { title: '名称', key: 'name' },
  { title: '类型', key: 'step_type' },
  { title: '适配器', key: 'adapter' },
  { title: '状态', key: 'status' },
  {
    title: '重试',
    key: 'retry',
    render: (row: WorkflowStep) => `${row.retry_count}/${row.retry_limit}`
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: WorkflowStep) =>
      h(
        NButton,
        { size: 'small', onClick: () => runWorkflowStep(row) },
        { default: () => '执行 Mock' }
      )
  }
]

onMounted(load)
</script>
