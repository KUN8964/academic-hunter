<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()

interface Brief {
  id: string
  subscription_type: string
  subscription_id: string
  date: string
  papers: { paper_id: string; rank: number; credibility_score: number | null }[]
  generated_at: string
}

interface Paper {
  id: string
  title: string
  authors: { name: string }[]
  abstract: string | null
  ai_abstract_zh: string | null
  ai_tags: string[]
  url: string
  venue: string | null
  venue_type: string | null
  source_type: string
  published_at: string | null
  credibility_score: number | null
  citation_count: number | null
}

const brief = ref<Brief | null>(null)
const papers = ref<Paper[]>([])
const loading = ref(true)
const error = ref('')

type Tier = 'all' | 'high' | 'medium' | 'low'
const activeTier = ref<Tier>('all')

const tierCounts = computed(() => {
  const c = { high: 0, medium: 0, low: 0 }
  for (const p of papers.value) {
    const s = p.credibility_score ?? 0
    if (s >= 8) c.high++
    else if (s >= 5) c.medium++
    else c.low++
  }
  return c
})

const filteredPapers = computed(() => {
  if (activeTier.value === 'all') return papers.value
  return papers.value.filter(p => {
    const s = p.credibility_score ?? 0
    if (activeTier.value === 'high') return s >= 8
    if (activeTier.value === 'medium') return s >= 5 && s < 8
    return s < 5
  })
})

const sourceLabels: Record<string, string> = {
  arxiv: 'arXiv',
  s2: 'Semantic Scholar',
  pubmed: 'PubMed',
}

function credibilityColor(score: number | null): string {
  if (score === null) return 'text-zinc-500'
  if (score >= 8) return 'text-red-400'
  if (score >= 5) return 'text-yellow-400'
  return 'text-green-400'
}

function credibilityBg(score: number | null): string {
  if (score === null) return 'bg-zinc-800'
  if (score >= 8) return 'bg-red-950/30 border-red-900/30'
  if (score >= 5) return 'bg-yellow-950/20 border-yellow-900/30'
  return 'bg-green-950/20 border-green-900/30'
}

function formatDate(d: string | null): string {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function tierLabel(t: Tier): string {
  if (t === 'high') return `🔴 高可信 (${tierCounts.value.high})`
  if (t === 'medium') return `🟡 中可信 (${tierCounts.value.medium})`
  if (t === 'low') return `🟢 待验证 (${tierCounts.value.low})`
  return `全部 (${papers.value.length})`
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/pipeline/briefs/${route.params.id}`)
    brief.value = data

    const paperIds: string[] = data.papers.map((p: any) => p.paper_id)
    const results = await Promise.all(
      paperIds.map((id: string) =>
        api.get(`/papers/${id}`).then(r => r.data).catch(() => null)
      )
    )
    papers.value = results.filter(Boolean) as Paper[]
  } catch (e: any) {
    error.value = e.response?.data?.detail || '加载简报失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="animate-pulse space-y-3">
        <div class="h-8 bg-zinc-800 rounded w-64" />
        <div class="h-4 bg-zinc-800 rounded w-48" />
        <div class="flex gap-3 mt-6">
          <div class="h-10 bg-zinc-800 rounded w-24" />
          <div class="h-10 bg-zinc-800 rounded w-24" />
          <div class="h-10 bg-zinc-800 rounded w-24" />
        </div>
      </div>
      <div v-for="i in 3" :key="i" class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse">
        <div class="h-5 bg-zinc-800 rounded w-3/4 mb-2" />
        <div class="h-3 bg-zinc-800 rounded w-1/2" />
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-20">
      <p class="text-red-400 mb-4">{{ error }}</p>
      <button @click="router.back()"
        class="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm transition">
        ← 返回
      </button>
    </div>

    <!-- Empty -->
    <div v-else-if="!brief" class="text-center py-20 text-zinc-500">
      <p>简报不存在</p>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Header -->
      <div class="mb-8">
        <button @click="router.push('/dashboard')"
          class="text-sm text-zinc-500 hover:text-zinc-300 transition mb-4 inline-flex items-center gap-1">
          ← 返回控制台
        </button>
        <h1 class="text-2xl font-bold text-white mb-2">
          {{ brief.subscription_type === 'researcher' ? '👤' : '📚' }}
          每日简报
        </h1>
        <p class="text-zinc-500 text-sm">
          {{ formatDate(brief.date) }}
          · 共 {{ papers.length }} 篇论文
          <span class="text-red-400 ml-2" v-if="tierCounts.high">{{ tierCounts.high }} 高可信</span>
          <span class="text-yellow-400 ml-1" v-if="tierCounts.medium">{{ tierCounts.medium }} 中可信</span>
          <span class="text-green-400 ml-1" v-if="tierCounts.low">{{ tierCounts.low }} 待验证</span>
        </p>
      </div>

      <!-- Tier tabs -->
      <div class="flex gap-2 mb-6 overflow-x-auto pb-1">
        <button
          v-for="t in (['all', 'high', 'medium', 'low'] as Tier[])"
          :key="t"
          @click="activeTier = t"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm transition whitespace-nowrap',
            activeTier === t
              ? 'bg-zinc-700 text-white'
              : 'bg-zinc-900 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
          ]">
          {{ tierLabel(t) }}
        </button>
      </div>

      <!-- Papers list -->
      <div v-if="filteredPapers.length === 0" class="text-center py-12 text-zinc-500">
        该层级暂无论文
      </div>
      <div class="space-y-3">
        <div
          v-for="paper in filteredPapers"
          :key="paper.id"
          @click="router.push(`/papers/${paper.id}`)"
          :class="credibilityBg(paper.credibility_score)"
          class="p-4 border rounded-lg hover:border-zinc-600 transition cursor-pointer group">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="text-white font-medium group-hover:text-blue-400 transition truncate">
                {{ paper.title }}
              </h3>
              <p class="text-zinc-500 text-sm mt-1">
                {{ paper.authors?.map(a => a.name).slice(0, 3).join(', ') }}
                {{ (paper.authors?.length || 0) > 3 ? ' et al.' : '' }}
              </p>
              <div class="flex items-center gap-3 mt-1.5 text-xs text-zinc-500">
                <span>{{ paper.venue || '预印本' }}</span>
                <span v-if="paper.published_at">· {{ formatDate(paper.published_at) }}</span>
                <span class="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-500">
                  {{ sourceLabels[paper.source_type] || paper.source_type }}
                </span>
              </div>
              <p v-if="paper.ai_abstract_zh" class="text-zinc-400 text-xs mt-2 leading-relaxed line-clamp-2">
                {{ paper.ai_abstract_zh }}
              </p>
            </div>
            <div class="text-right shrink-0">
              <span :class="credibilityColor(paper.credibility_score)" class="text-lg font-mono font-bold">
                {{ paper.credibility_score?.toFixed(1) ?? '-' }}
              </span>
              <p class="text-xs text-zinc-600 mt-0.5">可信度</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
