<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const brief = ref<any>(null)
const papers = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get(`/pipeline/briefs/${route.params.id}`)
    brief.value = data
    // Fetch paper details for each paper in the brief
    const paperIds = data.papers.map((p: any) => p.paper_id)
    const paperPromises = paperIds.map((id: string) =>
      api.get(`/papers/${id}`).then((r) => r.data).catch(() => null)
    )
    papers.value = (await Promise.all(paperPromises)).filter(Boolean)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <div v-if="loading" class="text-center py-20 text-zinc-500">加载中...</div>

    <div v-else-if="brief">
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-white mb-1">
          {{ brief.subscription_type === 'topic' ? '📚' : '👤' }}
          {{ brief.date }} 每日简报
        </h1>
        <p class="text-zinc-500 text-sm">共 {{ papers.length }} 篇论文</p>
      </div>

      <div class="space-y-4">
        <div v-for="paper in papers" :key="paper.id"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer"
          @click="router.push(`/papers/${paper.id}`)">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <h3 class="text-white font-medium truncate">{{ paper.title }}</h3>
              <p class="text-zinc-500 text-sm mt-1">
                {{ paper.authors?.map((a: any) => a.name).join(', ')?.slice(0, 80) }}
              </p>
              <p class="text-zinc-600 text-xs mt-1">
                {{ paper.venue || '预印本' }}
                <span v-if="paper.published_at"> · {{ new Date(paper.published_at).toLocaleDateString('zh-CN') }}</span>
              </p>
            </div>
            <div class="text-right shrink-0">
              <span
                :class="(paper.credibility_score || 0) >= 8 ? 'text-red-400' : (paper.credibility_score || 0) >= 5 ? 'text-yellow-400' : 'text-green-400'"
                class="text-sm font-mono">
                {{ paper.credibility_score?.toFixed(1) || '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
