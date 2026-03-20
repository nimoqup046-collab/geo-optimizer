<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      bordered
      show-trigger
      collapse-mode="width"
      :collapsed-width="64"
      :width="248"
      :native-scrollbar="false"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="logo">
        <n-icon size="30" color="#0ea5e9">
          <PulseOutline />
        </n-icon>
        <span v-if="!collapsed" class="logo-text">{{ UI_TEXT.layout.appTitle }}</span>
      </div>

      <n-menu
        v-model:value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :options="menuOptions"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="header">
        <n-space justify="space-between" align="center" style="width: 100%">
          <n-breadcrumb>
            <n-breadcrumb-item>{{ currentTitle }}</n-breadcrumb-item>
          </n-breadcrumb>
          <n-space align="center">
            <n-tag v-if="isDemoActive" type="success">{{ UI_TEXT.demo.badge }}</n-tag>
            <n-button size="small" tertiary @click="toggleMode">
              {{ isDemoActive ? UI_TEXT.demo.switchToReal : UI_TEXT.demo.switchToDemo }}
            </n-button>
            <n-input
              v-model:value="apiKeyInput"
              size="small"
              :placeholder="UI_TEXT.layout.apiKeyPlaceholder"
              type="password"
              show-password-on="click"
              style="width: 220px"
            />
            <n-button size="small" @click="saveKey">{{ UI_TEXT.layout.saveKey }}</n-button>
          </n-space>
        </n-space>
      </n-layout-header>
      <n-layout-content content-style="padding: 18px;" :native-scrollbar="false">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AlbumsOutline,
  ApertureOutline,
  CubeOutline,
  NewspaperOutline,
  PulseOutline,
  RocketOutline
} from '@vicons/ionicons5'
import { NIcon, useMessage } from 'naive-ui'
import { UI_TEXT } from '@/constants/uiText'
import { isDemoModeActive, setRealMode } from '@/services/demoMode'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const collapsed = ref(false)
const activeKey = ref((route.name as string) || 'Overview')
const apiKeyInput = ref(localStorage.getItem('geo_internal_api_key') || '')
const isDemoActive = ref(isDemoModeActive())

watch(
  () => route.name,
  (name) => {
    if (name) activeKey.value = String(name)
  }
)

const currentTitle = computed(() => String(route.meta.title || UI_TEXT.layout.defaultTitle))
const renderIcon = (icon: any) => () => h(NIcon, null, { default: () => h(icon) })

const menuOptions = [
  { label: UI_TEXT.layout.menu.overview, key: 'Overview', icon: renderIcon(PulseOutline) },
  { label: UI_TEXT.layout.menu.brands, key: 'Brands', icon: renderIcon(CubeOutline) },
  { label: UI_TEXT.layout.menu.assets, key: 'Assets', icon: renderIcon(AlbumsOutline) },
  { label: UI_TEXT.layout.menu.analysis, key: 'AnalysisCenter', icon: renderIcon(ApertureOutline) },
  { label: UI_TEXT.layout.menu.workshop, key: 'Workshop', icon: renderIcon(NewspaperOutline) },
  {
    label: UI_TEXT.layout.menu.distribution,
    key: 'DistributionFeedback',
    icon: renderIcon(RocketOutline)
  }
]

function handleMenuSelect(key: string): void {
  router.push({ name: key })
}

function saveKey(): void {
  localStorage.setItem('geo_internal_api_key', apiKeyInput.value.trim())
  message.success(UI_TEXT.layout.saveKeySuccess)
}

function toggleMode(): void {
  setRealMode(isDemoActive.value)
  message.success(isDemoActive.value ? UI_TEXT.demo.switchedToReal : UI_TEXT.demo.switchedToDemo)
  window.location.reload()
}
</script>

<style scoped>
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--n-border-color);
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
}

.header {
  display: flex;
  align-items: center;
  height: 58px;
  padding: 0 16px;
}
</style>
