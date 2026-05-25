<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth, getGuestConfig, setGuestConfig } from '../stores/auth'
import api from '../api'

const router = useRouter()

onMounted(() => {
  if (auth.token) {
    router.replace('/dashboard')
  }
})

// ── Guest flow: API key → topic → AI expand → search papers ──

type Step = 'enter' | 'topic' | 'expand' | 'papers'

const step = ref<Step>('enter')
const apiKey = ref(localStorage.getItem('guest_api_key') || '')
const baseUrl = ref(localStorage.getItem('guest_base_url') || 'https://api.deepseek.com/v1')
const model = ref(localStorage.getItem('guest_model') || 'deepseek-chat')
const queryText = ref('')
const loading = ref(false)
const error = ref('')
const keywords = ref<string[]>([])
const subfields = ref<string[]>([])
const researchers = ref<any[]>([])

// Paper search results
interface Paper {
  title: string
  authors: string[]
  abstract: string | null
  url: string
  venue: string | null
  source_type: string
  published_at: string | null
}
const papers = ref<Paper[]>([])
const totalPapers = ref(0)

function saveKeyAndContinue() {
  if (!apiKey.value.trim()) return
  setGuestConfig(apiKey.value.trim(), baseUrl.value.trim(), model.value.trim())
  step.value = 'topic'
}

async function doExpand() {
  if (!queryText.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const cfg = getGuestConfig()
    const { data } = await api.post('/public/onboarding/expand', {
      query_text: queryText.value.trim(),
      ai_api_key: cfg.ai_api_key,
      ai_base_url: cfg.ai_base_url,
      ai_model: cfg.ai_model,
    })
    keywords.value = data.ai_keywords || []
    subfields.value = data.suggested_subfields || []
    researchers.value = data.suggested_researchers || []
    step.value = 'expand'
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'AI 调用失败，请检查 API Key'
  } finally {
    loading.value = false
  }
}

async function searchPapers() {
  if (!keywords.value.length) return
  loading.value = true
  error.value = ''
  try {
    const cfg = getGuestConfig()
    const { data } = await api.post('/public/search', {
      keywords: keywords.value,
      ai_api_key: cfg.ai_api_key,
      ai_base_url: cfg.ai_base_url,
      ai_model: cfg.ai_model,
    })
    papers.value = data.papers
    totalPapers.value = data.total
    step.value = 'papers'
  } catch (e: any) {
    error.value = '论文搜索失败，请重试'
  } finally {
    loading.value = false
  }
}

function startOver() {
  step.value = 'topic'
  queryText.value = ''
  keywords.value = []
  subfields.value = []
  researchers.value = []
  papers.value = []
  totalPapers.value = 0
}

function truncate(s: string | null, n: number) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '...' : s
}
</script>

<template>
  <div class="min-h-[80vh] flex flex-col items-center justify-center px-6">
    <!-- Step 1: Enter API Key -->
    <div v-if="step === 'enter'" class="w-full max-w-md text-center">
      <h1 class="text-4xl font-bold text-white mb-3">🔬 Academic Hunter</h1>
      <p class="text-zinc-400 mb-10 text-lg">科研情报，即刻追踪 — 无需注册，填入 API Key 即可开始</p>

      <div class="space-y-4 text-left">
        <div>
          <label class="block text-sm text-zinc-400 mb-1">API Key</label>
          <input v-model="apiKey" type="password" placeholder="sk-..."
            class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>
        <div>
          <label class="block text-sm text-zinc-400 mb-1">API Base URL <span class="text-zinc-600">（可选）</span></label>
          <input v-model="baseUrl" type="text"
            class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>
        <div>
          <label class="block text-sm text-zinc-400 mb-1">模型 <span class="text-zinc-600">（可选）</span></label>
          <input v-model="model" type="text" placeholder="deepseek-chat"
            class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>
        <button @click="saveKeyAndContinue" :disabled="!apiKey.trim()"
          class="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
          开始使用 →
        </button>
      </div>

      <div class="mt-8 pt-6 border-t border-zinc-800 space-y-3">
        <p class="text-sm text-zinc-500">需要持久化订阅和每日简报？</p>
        <router-link to="/register" class="block w-full py-2.5 border border-zinc-700 hover:border-zinc-500 text-zinc-300 rounded-lg text-sm transition">注册账户</router-link>
        <router-link to="/login" class="block w-full py-2.5 border border-zinc-700 hover:border-zinc-500 text-zinc-300 rounded-lg text-sm transition">已有账户？登录</router-link>
      </div>
    </div>

    <!-- Step 2: Research topic -->
    <div v-if="step === 'topic'" class="w-full max-w-lg">
      <h2 class="text-2xl font-bold text-white mb-2">你想追踪什么研究方向？</h2>
      <p class="text-zinc-500 mb-6">用自然语言描述，AI 会帮你扩展关键词和推荐研究者</p>
      <textarea v-model="queryText" rows="4"
        placeholder="例如：大模型推理优化，特别是量化和投机解码方向..."
        class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition resize-none mb-4"></textarea>
      <p v-if="error" class="text-red-400 text-sm mb-4">{{ error }}</p>
      <div class="flex gap-3">
        <button @click="step = 'enter'" class="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition">← 返回</button>
        <button @click="doExpand" :disabled="loading || !queryText.trim()"
          class="flex-1 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
          {{ loading ? 'AI 分析中...' : '分析研究方向 →' }}
        </button>
      </div>
    </div>

    <!-- Step 3: AI expansion results -->
    <div v-if="step === 'expand'" class="w-full max-w-lg">
      <h2 class="text-2xl font-bold text-white mb-6">AI 分析结果</h2>

      <div v-if="keywords.length" class="mb-6">
        <p class="text-sm text-zinc-400 mb-2">关键词：</p>
        <div class="flex flex-wrap gap-2">
          <span v-for="kw in keywords" :key="kw" class="px-2.5 py-1.5 bg-zinc-800 text-zinc-200 text-sm rounded-lg">{{ kw }}</span>
        </div>
      </div>
      <div v-if="subfields.length" class="mb-6">
        <p class="text-sm text-zinc-400 mb-2">相关子领域：</p>
        <div class="flex flex-wrap gap-2">
          <span v-for="sf in subfields" :key="sf" class="px-2.5 py-1.5 bg-zinc-800 text-zinc-200 text-sm rounded-lg">{{ sf }}</span>
        </div>
      </div>
      <div v-if="researchers.length" class="mb-8">
        <p class="text-sm text-zinc-400 mb-2">建议关注的研究者：</p>
        <div class="space-y-2">
          <div v-for="r in researchers" :key="r.name" class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
            <span class="text-white text-sm">{{ r.name }}</span>
          </div>
        </div>
      </div>

      <p v-if="error" class="text-red-400 text-sm mb-4">{{ error }}</p>

      <button @click="searchPapers" :disabled="loading || !keywords.length"
        class="w-full py-3 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-lg font-medium transition mb-3">
        {{ loading ? '搜索中...' : '🔍 用这些关键词搜索论文' }}
      </button>
      <div class="flex gap-3">
        <button @click="startOver" class="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition">换一个方向</button>
        <router-link to="/register" class="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-center transition">注册以保存订阅 →</router-link>
      </div>
    </div>

    <!-- Step 4: Paper results -->
    <div v-if="step === 'papers'" class="w-full max-w-2xl">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-white">搜索结果 <span class="text-zinc-500 text-lg font-normal">({{ totalPapers }} 篇)</span></h2>
        <button @click="step = 'expand'" class="text-sm text-zinc-400 hover:text-white transition">← 返回分析</button>
      </div>

      <p v-if="error" class="text-red-400 text-sm mb-4">{{ error }}</p>

      <div class="space-y-3">
        <div v-for="paper in papers" :key="paper.url"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition">
          <a :href="paper.url" target="_blank" class="text-white font-medium hover:text-blue-400 transition block mb-1">
            {{ paper.title }}
          </a>
          <p class="text-zinc-500 text-xs mb-1">
            {{ paper.authors.slice(0, 3).join(', ') }}{{ paper.authors.length > 3 ? ' et al.' : '' }}
            <span v-if="paper.venue" class="text-zinc-600 ml-2">{{ paper.venue }}</span>
          </p>
          <p v-if="paper.abstract" class="text-zinc-500 text-xs leading-relaxed mt-2">
            {{ truncate(paper.abstract, 200) }}
          </p>
          <div class="flex items-center gap-3 mt-2 text-xs">
            <span class="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-500">{{ paper.source_type }}</span>
            <span v-if="paper.published_at" class="text-zinc-600">{{ paper.published_at.slice(0, 10) }}</span>
          </div>
        </div>
      </div>

      <div class="bg-amber-950/20 border border-amber-900/30 rounded-lg p-4 mt-8 mb-4">
        <p class="text-amber-400 text-sm">
          以上为即时搜索结果。注册账户可获得：每日自动简报、AI 中文摘要、论文可信度评分等持久化功能。
        </p>
      </div>
      <router-link to="/register"
        class="block w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-center transition">
        注册以保存订阅 →
      </router-link>
      <button @click="step = 'topic'"
        class="w-full py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg mt-3 transition">
        搜索其他方向
      </button>
    </div>
  </div>
</template>
