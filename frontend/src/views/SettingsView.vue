<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { auth, getGuestConfig, setGuestConfig } from '../stores/auth'
import api from '../api'

interface Settings {
  ai_api_key_masked: string | null
  ai_base_url: string | null
  ai_model: string | null
  s2_api_key_masked: string | null
}

const isLoggedIn = () => !!auth.token

const settings = ref<Settings>({ ai_api_key_masked: null, ai_base_url: null, ai_model: null, s2_api_key_masked: null })
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')

const form = ref({
  ai_api_key: '',
  ai_base_url: '',
  ai_model: '',
  s2_api_key: '',
})

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  loading.value = true
  if (isLoggedIn()) {
    try {
      const { data } = await api.get('/auth/settings')
      settings.value = data
      form.value.ai_base_url = data.ai_base_url || ''
      form.value.ai_model = data.ai_model || ''
    } catch {
      // Ignore — settings not available
    }
  } else {
    // Guest mode: load from localStorage
    const cfg = getGuestConfig()
    form.value.ai_base_url = cfg.ai_base_url
    form.value.ai_model = cfg.ai_model
    if (cfg.ai_api_key) {
      settings.value.ai_api_key_masked = 'sk-...' + cfg.ai_api_key.slice(-4)
    }
    if (cfg.s2_api_key) {
      settings.value.s2_api_key_masked = '...' + cfg.s2_api_key.slice(-4)
    }
  }
  loading.value = false
}

async function saveSettings() {
  saving.value = true
  message.value = ''
  error.value = ''

  if (isLoggedIn()) {
    const payload: Record<string, string | null> = {}
    if (form.value.ai_api_key) payload.ai_api_key = form.value.ai_api_key
    if (form.value.ai_base_url) payload.ai_base_url = form.value.ai_base_url
    else payload.ai_base_url = null
    if (form.value.ai_model) payload.ai_model = form.value.ai_model
    else payload.ai_model = null
    if (form.value.s2_api_key) payload.s2_api_key = form.value.s2_api_key
    else payload.s2_api_key = null

    try {
      const { data } = await api.put('/auth/settings', payload)
      settings.value = data
      form.value.ai_api_key = ''
      message.value = '设置已保存'
    } catch (e: any) {
      error.value = e.response?.data?.detail || '保存失败'
    }
  } else {
    // Guest mode: save to localStorage
    setGuestConfig(
      form.value.ai_api_key || getGuestConfig().ai_api_key,
      form.value.ai_base_url,
      form.value.ai_model,
    )
    if (form.value.s2_api_key) {
      localStorage.setItem('guest_s2_key', form.value.s2_api_key)
    } else if (form.value.s2_api_key === '') {
      localStorage.removeItem('guest_s2_key')
    }
    const cfg = getGuestConfig()
    if (cfg.ai_api_key) {
      settings.value.ai_api_key_masked = 'sk-...' + cfg.ai_api_key.slice(-4)
    }
    form.value.ai_api_key = ''
    form.value.s2_api_key = ''
    message.value = '设置已保存到本地'
  }

  saving.value = false
}

const modelPresets = [
  { label: 'DeepSeek V3', value: 'deepseek-chat' },
  { label: 'DeepSeek R1', value: 'deepseek-reasoner' },
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'GPT-4o-mini', value: 'gpt-4o-mini' },
  { label: 'Claude 3.5 Sonnet', value: 'claude-3-5-sonnet-20241022' },
  { label: '自定义...', value: '' },
]
</script>

<template>
  <div class="max-w-2xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold text-white mb-2">AI 模型设置</h1>
    <p class="text-zinc-500 mb-2">
      <template v-if="isLoggedIn()">配置你自己的 AI 提供商。未设置时使用服务器默认。</template>
      <template v-else>配置你的 API Key。数据仅保存在浏览器本地，不会上传服务器。</template>
    </p>
    <p v-if="!isLoggedIn()" class="text-xs text-amber-400 mb-6">
      当前为访客模式 — 注册账户可云端保存设置并获得每日简报等持久化功能
    </p>

    <div v-if="loading" class="text-center py-10 text-zinc-500">加载中...</div>

    <div v-else class="space-y-6">
      <!-- API Key -->
      <div>
        <label class="block text-sm text-zinc-400 mb-1">API Key</label>
        <input v-model="form.ai_api_key" type="password"
          :placeholder="settings.ai_api_key_masked ? '已设置 (' + settings.ai_api_key_masked + ')' : 'sk-...'"
          class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        <p class="text-xs text-zinc-600 mt-1">留空保持当前设置不变</p>
      </div>

      <!-- Base URL -->
      <div>
        <label class="block text-sm text-zinc-400 mb-1">API Base URL</label>
        <input v-model="form.ai_base_url" type="text"
          placeholder="https://api.deepseek.com/v1"
          class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        <p class="text-xs text-zinc-600 mt-1">OpenAI 兼容的 API 地址</p>
      </div>

      <!-- Model -->
      <div>
        <label class="block text-sm text-zinc-400 mb-1">模型</label>
        <div class="grid grid-cols-2 gap-2 mb-3">
          <button v-for="preset in modelPresets" :key="preset.value || '__custom'"
            @click="form.ai_model = preset.value"
            :class="form.ai_model === preset.value ? 'bg-blue-600 border-blue-500 text-white' : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:border-zinc-600'"
            class="px-3 py-2 border rounded-lg text-sm text-left transition">
            {{ preset.label }}
          </button>
        </div>
        <input v-if="!modelPresets.slice(0, -1).some(p => p.value === form.ai_model)"
          v-model="form.ai_model" type="text"
          placeholder="输入模型名称"
          class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        <p class="text-xs text-zinc-600 mt-1">
          当前：
          <template v-if="isLoggedIn()">{{ settings.ai_model || '服务器默认 (deepseek-chat)' }}</template>
          <template v-else>{{ form.ai_model || 'deepseek-chat' }}</template>
        </p>
      </div>

      <!-- S2 API Key -->
      <div>
        <label class="block text-sm text-zinc-400 mb-1">Semantic Scholar API Key <span class="text-zinc-600">（可选，提高搜索限额）</span></label>
        <input v-model="form.s2_api_key" type="password"
          :placeholder="settings.s2_api_key_masked ? '已设置 (' + settings.s2_api_key_masked + ')' : '留空则仅使用 arXiv 搜索'"
          class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        <p class="text-xs text-zinc-600 mt-1">
          <a href="https://www.semanticscholar.org/product/api#api-key-form" target="_blank" class="text-blue-400 hover:underline">免费获取</a>，留空则仅使用 arXiv 搜索
        </p>
      </div>

      <!-- Messages -->
      <p v-if="message" class="text-green-400 text-sm">{{ message }}</p>
      <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

      <!-- Save -->
      <button @click="saveSettings" :disabled="saving"
        class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </div>
  </div>
</template>
