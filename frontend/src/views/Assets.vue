<template>
  <n-space vertical :size="16">
    <n-alert v-if="loadError" type="error" :show-icon="false">{{ loadError }}</n-alert>

    <n-card :title="UI_TEXT.assets.uploadTitle" :bordered="false">
      <n-space vertical :size="10">
        <n-space>
          <n-select
            v-model:value="selectedBrandId"
            :options="brandOptions"
            :placeholder="UI_TEXT.assets.selectBrand"
            style="width: 260px"
          />
          <n-upload
            :custom-request="handleUpload"
            :show-file-list="false"
            accept=".txt,.md,.csv,.doc,.docx,.pdf,.xls,.xlsx,.png,.jpg,.jpeg,.webp"
          >
            <n-button>{{ UI_TEXT.assets.uploadFile }}</n-button>
          </n-upload>
          <n-button :loading="folderUploading" :disabled="folderUploading" @click="openFolderPicker">
            上传文件夹
          </n-button>
          <n-button :loading="folderUploading" :disabled="folderUploading" @click="openBatchPicker">
            兼容模式：批量文件
          </n-button>
          <n-button :loading="loading" @click="load">{{ UI_TEXT.common.refresh }}</n-button>
        </n-space>

        <n-text depth="3">
          支持选整个文件夹（含子目录）。若浏览器不支持目录选择，请使用“兼容模式：批量文件”。
        </n-text>

        <n-progress
          v-if="folderUploading"
          type="line"
          :percentage="folderProgress"
          :indicator-placement="'inside'"
          processing
        />
        <n-text v-if="folderUploading">{{ folderStatusText }}</n-text>
      </n-space>

      <input
        ref="folderInputRef"
        type="file"
        multiple
        webkitdirectory
        directory
        mozdirectory
        msdirectory
        odirectory
        style="display: none"
        @change="handleFolderChange"
      />
      <input
        ref="batchInputRef"
        type="file"
        multiple
        accept=".txt,.md,.csv,.doc,.docx,.pdf,.xls,.xlsx,.png,.jpg,.jpeg,.webp"
        style="display: none"
        @change="handleBatchChange"
      />
    </n-card>

    <n-card :title="UI_TEXT.assets.pasteTitle" :bordered="false">
      <n-form :model="pasteForm">
        <n-form-item label="标题">
          <n-input v-model:value="pasteForm.title" placeholder="请输入标题" />
        </n-form-item>
        <n-form-item label="平台">
          <n-input v-model:value="pasteForm.platform" placeholder="wechat / zhihu / xiaohongshu / video" />
        </n-form-item>
        <n-form-item label="正文">
          <n-input v-model:value="pasteForm.raw_text" type="textarea" :rows="8" />
        </n-form-item>
      </n-form>
      <n-button type="primary" @click="pasteAsset">{{ UI_TEXT.assets.saveText }}</n-button>
    </n-card>

    <n-card :title="UI_TEXT.assets.listTitle" :bordered="false">
      <n-data-table :columns="columns" :data="assets" :bordered="false" />
      <n-empty v-if="assets.length === 0" description="暂无素材，请先上传或粘贴内容。" />
    </n-card>
  </n-space>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { assetApi, brandApi, type SourceAsset } from '@/api'
import { UI_TEXT } from '@/constants/uiText'

const message = useMessage()
const brands = ref<any[]>([])
const assets = ref<SourceAsset[]>([])
const selectedBrandId = ref('')
const loading = ref(false)
const loadError = ref('')

const folderInputRef = ref<HTMLInputElement | null>(null)
const batchInputRef = ref<HTMLInputElement | null>(null)
const folderUploading = ref(false)
const folderProgress = ref(0)
const folderStatusText = ref('')

const MAX_UPLOAD_SIZE = 10 * 1024 * 1024
const UPLOADABLE_EXTENSIONS = new Set([
  '.txt',
  '.md',
  '.csv',
  '.doc',
  '.docx',
  '.pdf',
  '.xls',
  '.xlsx',
  '.png',
  '.jpg',
  '.jpeg',
  '.webp'
])

const pasteForm = reactive({
  title: '',
  platform: 'wechat',
  raw_text: ''
})

const brandOptions = computed(() => brands.value.map((brand) => ({ label: brand.name, value: brand.id })))

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    brands.value = await brandApi.list()
    if (!selectedBrandId.value && brands.value.length > 0) selectedBrandId.value = brands.value[0].id
    assets.value = await assetApi.list(selectedBrandId.value ? { brand_id: selectedBrandId.value } : undefined)
  } catch (error: any) {
    loadError.value = `${UI_TEXT.common.loadingFailed}: ${error?.message || UI_TEXT.common.unknownError}`
  } finally {
    loading.value = false
  }
}

const fileExt = (name: string) => {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

const uploadSingleFile = async (rawFile: File, titleOverride?: string) => {
  const formData = new FormData()
  formData.append('file', rawFile)
  formData.append('brand_id', selectedBrandId.value)
  formData.append('title', titleOverride || rawFile.name)
  formData.append('platform', 'mixed')
  await assetApi.upload(formData)
}

const handleUpload = async ({ file }: any) => {
  if (!selectedBrandId.value) {
    message.warning('请先选择品牌')
    return
  }
  try {
    await uploadSingleFile(file.file, file.name)
    message.success('素材上传成功')
    await load()
  } catch (error: any) {
    message.error(`上传失败：${error?.message || UI_TEXT.common.unknownError}`)
  }
}

const normalizeEntries = (files: File[], useRelativePath: boolean) =>
  files.map((f) => {
    const relativePath = useRelativePath
      ? ((f as any).webkitRelativePath || f.name).replace(/\\/g, '/')
      : f.name
    return { file: f, relativePath }
  })

const uploadEntries = async (entries: Array<{ file: File; relativePath: string }>) => {
  const sizeSkipped = entries.filter((item) => item.file.size > MAX_UPLOAD_SIZE).length
  const extSkipped = entries.filter(
    (item) => item.file.size <= MAX_UPLOAD_SIZE && !UPLOADABLE_EXTENSIONS.has(fileExt(item.file.name))
  ).length
  const accepted = entries.filter(
    (item) => item.file.size <= MAX_UPLOAD_SIZE && UPLOADABLE_EXTENSIONS.has(fileExt(item.file.name))
  )

  if (accepted.length === 0) {
    message.warning('没有可上传文件：请检查文件类型或大小（单文件不超过 10MB）')
    return
  }

  folderUploading.value = true
  folderProgress.value = 0
  folderStatusText.value = `准备上传 ${accepted.length} 个文件...`

  let success = 0
  let failed = 0
  for (let i = 0; i < accepted.length; i += 1) {
    const current = accepted[i]
    try {
      await uploadSingleFile(current.file, current.relativePath)
      success += 1
    } catch {
      failed += 1
    }
    folderProgress.value = Math.round(((i + 1) / accepted.length) * 100)
    folderStatusText.value = `上传中 ${i + 1}/${accepted.length}（成功 ${success}，失败 ${failed}）`
  }

  folderUploading.value = false
  folderStatusText.value = ''

  const summary = `成功 ${success}，失败 ${failed}，类型跳过 ${extSkipped}，大小跳过 ${sizeSkipped}`
  if (failed === 0) {
    message.success(`批量上传完成：${summary}`)
  } else {
    message.warning(`批量上传完成：${summary}`)
  }
  await load()
}

const collectFilesFromDirectoryHandle = async (
  dirHandle: any,
  prefix = ''
): Promise<Array<{ file: File; relativePath: string }>> => {
  const entries: Array<{ file: File; relativePath: string }> = []
  for await (const [name, handle] of dirHandle.entries()) {
    if (handle.kind === 'file') {
      const file = await handle.getFile()
      entries.push({ file, relativePath: `${prefix}${name}` })
      continue
    }
    if (handle.kind === 'directory') {
      const children = await collectFilesFromDirectoryHandle(handle, `${prefix}${name}/`)
      entries.push(...children)
    }
  }
  return entries
}

const openFolderPicker = async () => {
  if (!selectedBrandId.value) {
    message.warning('请先选择品牌')
    return
  }

  const picker = (window as any).showDirectoryPicker
  if (typeof picker === 'function') {
    try {
      const directoryHandle = await picker({ id: 'geo-assets-folder', mode: 'read' })
      const entries = await collectFilesFromDirectoryHandle(directoryHandle)
      await uploadEntries(entries)
    } catch (error: any) {
      if (error?.name !== 'AbortError') {
        message.warning('目录选择失败，已回退到兼容模式')
      }
      openLegacyFolderPicker()
    }
    return
  }

  openLegacyFolderPicker()
}

const openLegacyFolderPicker = () => {
  const input = folderInputRef.value
  if (!input) return
  input.setAttribute('webkitdirectory', '')
  input.setAttribute('directory', '')
  input.click()
}

const openBatchPicker = () => {
  if (!selectedBrandId.value) {
    message.warning('请先选择品牌')
    return
  }
  batchInputRef.value?.click()
}

const handleFolderChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const fileList = input.files
  if (!fileList || fileList.length === 0) {
    input.value = ''
    return
  }
  await uploadEntries(normalizeEntries(Array.from(fileList), true))
  input.value = ''
}

const handleBatchChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const fileList = input.files
  if (!fileList || fileList.length === 0) {
    input.value = ''
    return
  }
  await uploadEntries(normalizeEntries(Array.from(fileList), false))
  input.value = ''
}

const pasteAsset = async () => {
  if (!selectedBrandId.value) {
    message.warning('请先选择品牌')
    return
  }
  if (!pasteForm.raw_text.trim()) {
    message.warning('正文不能为空')
    return
  }
  await assetApi.paste({
    brand_id: selectedBrandId.value,
    title: pasteForm.title || '粘贴素材',
    platform: pasteForm.platform,
    raw_text: pasteForm.raw_text
  })
  message.success('文本素材已保存')
  pasteForm.title = ''
  pasteForm.raw_text = ''
  await load()
}

const columns = [
  { title: '标题', key: 'title' },
  { title: '类型', key: 'source_type' },
  { title: '平台', key: 'platform' },
  { title: '状态', key: 'status' },
  { title: '摘要', key: 'summary' }
]

onMounted(load)
</script>
