<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const query = ref('')
const results = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const searched = ref(false)
const error = ref('')

const HISTORY_KEY = 'search_history'
const MAX_HISTORY = 5
const history = ref<string[]>([])

onMounted(() => {
  try {
    history.value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch { history.value = [] }
})

function saveHistory(q: string) {
  const clean = q.trim()
  if (!clean) return
  history.value = [clean, ...history.value.filter(h => h !== clean)].slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}

const sourceLabels: Record<string, string> = {
  arxiv: 'arXiv',
  s2: 'Semantic Scholar',
  pubmed: 'PubMed',
}
const sourceColors: Record<string, string> = {
  arxiv: 'bg-red-950/30 text-red-400 border-red-900/30',
  s2: 'bg-blue-950/30 text-blue-400 border-blue-900/30',
  pubmed: 'bg-green-950/30 text-green-400 border-green-900/30',
}

function credibilityColor(score: number | null): string {
  if (score === null) return 'text-zinc-500'
  if (score >= 8) return 'text-red-400'
  if (score >= 5) return 'text-yellow-400'
  return 'text-green-400'
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function doSearch(immediate = false) {
  const q = query.value.trim()
  if (!q) return

  if (!immediate) {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => executeSearch(q), 300)
    return
  }
  if (debounceTimer) clearTimeout(debounceTimer)
  executeSearch(q)
}

async function executeSearch(q: string) {
  loading.value = true
  searched.value = true
  error.value = ''
  saveHistory(q)
  try {
    const { data } = await api.get('/papers', { params: { q, limit: 30 } })
    results.value = data.results
    total.value = data.total
  } catch (e: any) {
    error.value = e.response?.data?.detail || '搜索失败，请重试'
    results.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function clearSearch() {
  query.value = ''
  results.value = []
  total.value = 0
  searched.value = false
  error.value = ''
}

function useHistory(q: string) {
  query.value = q
  doSearch(true)
}

function formatDate(d: string | null): string {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

// Keyboard shortcut: / to focus search
function onKeydown(e: KeyboardEvent) {
  if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
    e.preventDefault()
    const input = document.querySelector<HTMLInputElement>('input[type="text"]')
    input?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold text-white mb-6">论文搜索</h1>

    <!-- Search bar -->
    <div class="flex gap-3 mb-6">
      <div class="flex-1 relative">
        <input
          v-model="query"
          @input="doSearch()"
          @keyup.enter="doSearch(true)"
          type="text"
          placeholder="搜索论文标题或摘要...  按 / 聚焦"
          class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition pr-10" />
        <button
          v-if="query"
          @click="clearSearch"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition">
          ✕
        </button>
      </div>
      <button
        @click="doSearch(true)"
        :disabled="loading || !query.trim()"
        class="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm transition">
        {{ loading ? '搜索中...' : '搜索' }}
      </button>
    </div>

    <!-- Search history -->
    <div v-if="!searched && history.length > 0" class="mb-8">
      <p class="text-xs text-zinc-600 mb-2">最近搜索</p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="h in history"
          :key="h"
          @click="useHistory(h)"
          class="px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-400 hover:text-white hover:border-zinc-600 transition">
          {{ h }}
        </button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-4 bg-red-950/20 border border-red-900/30 rounded-lg mb-6">
      <p class="text-red-400 text-sm">{{ error }}</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse">
        <div class="h-5 bg-zinc-800 rounded w-3/4 mb-2" />
        <div class="h-3 bg-zinc-800 rounded w-1/2 mb-1" />
        <div class="h-3 bg-zinc-800 rounded w-1/3" />
      </div>
    </div>

    <!-- Initial state -->
    <div v-else-if="!searched" class="text-center py-20">
      <p class="text-2xl mb-3">🔍</p>
      <p class="text-zinc-500 text-lg mb-2">输入关键词搜索论文</p>
      <p class="text-zinc-600 text-sm">支持英文标题、摘要全文检索</p>
    </div>

    <!-- No results -->
    <div v-else-if="results.length === 0" class="text-center py-16">
      <p class="text-zinc-500 text-lg mb-2">未找到相关论文</p>
      <p class="text-zinc-600 text-sm mb-4">试试用英文关键词，或减少搜索词</p>
      <button @click="clearSearch" class="text-blue-400 hover:text-blue-300 text-sm transition">清除搜索</button>
    </div>

    <!-- Results -->
    <div v-else>
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm text-zinc-500">找到 {{ total }} 篇论文</p>
        <button @click="clearSearch" class="text-xs text-zinc-600 hover:text-zinc-400 transition">清除</button>
      </div>

      <div class="space-y-3">
        <div
          v-for="paper in results"
          :key="paper.id"
          @click="router.push(`/papers/${paper.id}`)"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-600 transition cursor-pointer group">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="text-white font-medium group-hover:text-blue-400 transition line-clamp-2">
                {{ paper.title }}
              </h3>
              <p class="text-zinc-500 text-sm mt-1">
                {{ paper.authors?.map((a: any) => a.name).slice(0, 3).join(', ') }}
                {{ (paper.authors?.length || 0) > 3 ? ' et al.' : '' }}
              </p>
              <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                <span v-if="paper.venue" class="text-xs text-zinc-600">{{ paper.venue }}</span>
                <span
                  v-if="paper.source_type"
                  :class="sourceColors[paper.source_type] || 'bg-zinc-800 text-zinc-400'"
                  class="px-1.5 py-0.5 rounded text-xs border">
                  {{ sourceLabels[paper.source_type] || paper.source_type }}
                </span>
                <span v-if="paper.published_at" class="text-xs text-zinc-600">{{ formatDate(paper.published_at) }}</span>
              </div>
            </div>
            <div class="text-right shrink-0" v-if="paper.credibility_score != null">
              <span :class="credibilityColor(paper.credibility_score)" class="text-lg font-mono font-bold">
                {{ paper.credibility_score.toFixed(1) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
