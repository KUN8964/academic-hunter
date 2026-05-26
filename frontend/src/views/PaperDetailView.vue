<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()

const paper = ref<any>(null)
const loading = ref(true)
const error = ref('')
const copied = ref(false)

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

const credibilityBadge = computed(() => {
  const s = paper.value?.credibility_score
  if (s == null) return { label: '未评分', color: 'text-zinc-500 bg-zinc-800' }
  if (s >= 8) return { label: '高可信', color: 'text-red-400 bg-red-950/30 border-red-900/30' }
  if (s >= 5) return { label: '中可信', color: 'text-yellow-400 bg-yellow-950/20 border-yellow-900/30' }
  return { label: '待验证', color: 'text-green-400 bg-green-950/20 border-green-900/30' }
})

function formatDate(d: string | null): string {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}

function buildCitation(): string {
  const p = paper.value
  if (!p) return ''
  const authors = (p.authors || []).map((a: any) => a.name).join(', ')
  const year = p.published_at ? new Date(p.published_at).getFullYear() : 'n.d.'
  const venue = p.venue || 'Unknown venue'
  return `${authors} (${year}). ${p.title}. ${venue}.`
}

async function copyCitation() {
  try {
    await navigator.clipboard.writeText(buildCitation())
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = buildCitation()
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

function searchTag(tag: string) {
  router.push({ path: '/search', query: { q: tag } })
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/papers/${route.params.id}`)
    paper.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '加载论文失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4 animate-pulse">
      <div class="h-4 bg-zinc-800 rounded w-20" />
      <div class="h-8 bg-zinc-800 rounded w-full" />
      <div class="h-4 bg-zinc-800 rounded w-1/2" />
      <div class="h-24 bg-zinc-800 rounded" />
      <div class="h-24 bg-zinc-800 rounded" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-20">
      <p class="text-red-400 mb-4">{{ error }}</p>
      <button @click="goBack"
        class="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm transition">
        ← 返回
      </button>
    </div>

    <!-- Content -->
    <template v-else-if="paper">
      <!-- Navigation -->
      <div class="flex items-center justify-between mb-6">
        <button @click="goBack"
          class="text-sm text-zinc-500 hover:text-zinc-300 transition inline-flex items-center gap-1">
          ← 返回
        </button>
        <button
          @click="copyCitation"
          class="text-sm px-3 py-1.5 bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-400 hover:text-white rounded-lg transition inline-flex items-center gap-1.5">
          {{ copied ? '✓ 已复制' : '📋 复制引用' }}
        </button>
      </div>

      <!-- Title -->
      <h1 class="text-2xl font-bold text-white mb-4 leading-snug">{{ paper.title }}</h1>

      <!-- Authors -->
      <p class="text-zinc-400 text-sm mb-3">
        {{ paper.authors?.map((a: any) => a.name).join(', ') || '未知作者' }}
      </p>

      <!-- Meta bar -->
      <div class="flex items-center gap-3 flex-wrap mb-6">
        <span
          :class="credibilityBadge.color"
          class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold border">
          {{ paper.credibility_score?.toFixed(1) ?? '-' }} {{ credibilityBadge.label }}
        </span>
        <span
          v-if="paper.source_type"
          :class="sourceColors[paper.source_type] || 'bg-zinc-800 text-zinc-400'"
          class="px-2 py-0.5 rounded text-xs border">
          {{ sourceLabels[paper.source_type] || paper.source_type }}
        </span>
        <span v-if="paper.venue" class="text-xs text-zinc-500">{{ paper.venue }}</span>
        <span v-if="paper.venue_type" class="text-xs text-zinc-600">{{ paper.venue_type }}</span>
        <span v-if="paper.published_at" class="text-xs text-zinc-500">· {{ formatDate(paper.published_at) }}</span>
      </div>

      <!-- Venue type-specific info -->
      <div v-if="paper.source_type === 'pubmed' && paper.source_metadata?.mesh_terms?.length"
        class="mb-6 p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
        <p class="text-xs text-zinc-500 mb-2">MeSH 术语</p>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="mh in paper.source_metadata.mesh_terms" :key="mh"
            class="px-2 py-0.5 bg-zinc-800 text-zinc-500 text-xs rounded">{{ mh }}</span>
        </div>
      </div>

      <!-- Citation count -->
      <div v-if="paper.citation_count != null" class="mb-6">
        <span class="text-xs text-zinc-500">被引 {{ paper.citation_count }} 次</span>
      </div>

      <!-- AI Chinese Summary -->
      <div v-if="paper.ai_abstract_zh" class="mb-6 p-4 bg-blue-950/20 border border-blue-900/30 rounded-lg">
        <p class="text-xs text-blue-400 mb-2 font-medium">AI 中文摘要</p>
        <p class="text-zinc-300 text-sm leading-relaxed">{{ paper.ai_abstract_zh }}</p>
      </div>

      <!-- AI Evaluation -->
      <div v-if="paper.ai_evaluation" class="mb-6 p-4 bg-amber-950/20 border border-amber-900/30 rounded-lg">
        <p class="text-xs text-amber-400 mb-2 font-medium">AI 评价</p>
        <p class="text-zinc-300 text-sm leading-relaxed">{{ paper.ai_evaluation }}</p>
      </div>

      <!-- Original Abstract -->
      <div v-if="paper.abstract" class="mb-6">
        <p class="text-xs text-zinc-500 mb-2 font-medium">摘要</p>
        <p class="text-zinc-400 text-sm leading-relaxed">{{ paper.abstract }}</p>
      </div>

      <!-- AI Tags -->
      <div v-if="paper.ai_tags?.length" class="mb-6">
        <p class="text-xs text-zinc-500 mb-2 font-medium">标签</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tag in paper.ai_tags"
            :key="tag"
            @click="searchTag(tag)"
            class="px-2.5 py-1 bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700 text-xs rounded transition cursor-pointer">
            {{ tag }}
          </button>
        </div>
      </div>

      <!-- Source URLs -->
      <div class="flex flex-wrap gap-3 pt-2 border-t border-zinc-800">
        <a v-if="paper.url" :href="paper.url" target="_blank"
          class="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition">
          {{ paper.source_type === 'pubmed' ? 'PubMed' : '查看原文' }} ↗
        </a>
        <a v-if="paper.doi" :href="`https://doi.org/${paper.doi}`" target="_blank"
          class="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300 transition">
          DOI: {{ paper.doi }}
        </a>
      </div>
    </template>
  </div>
</template>
