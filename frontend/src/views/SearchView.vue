<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const query = ref('')
const results = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const searched = ref(false)

async function doSearch() {
  if (!query.value.trim()) return
  loading.value = true
  searched.value = true
  try {
    const { data } = await api.get('/papers', { params: { q: query.value.trim(), limit: 20 } })
    results.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold text-white mb-6">论文搜索</h1>

    <div class="flex gap-3 mb-8">
      <input v-model="query" @keyup.enter="doSearch" type="text"
        placeholder="搜索论文标题或摘要..."
        class="flex-1 px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
      <button @click="doSearch" :disabled="loading || !query.trim()"
        class="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition">
        搜索
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-10 text-zinc-500">搜索中...</div>

    <!-- Empty -->
    <div v-else-if="searched && results.length === 0" class="text-center py-10">
      <p class="text-zinc-500">未找到相关论文</p>
    </div>

    <!-- Results -->
    <div v-else-if="results.length > 0">
      <p class="text-sm text-zinc-500 mb-4">找到 {{ total }} 篇论文</p>
      <div class="space-y-3">
        <div v-for="paper in results" :key="paper.id"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer"
          @click="router.push(`/papers/${paper.id}`)">
          <h3 class="text-white font-medium truncate">{{ paper.title }}</h3>
          <p class="text-zinc-500 text-sm mt-1">
            {{ paper.authors?.map((a: any) => a.name).join(', ')?.slice(0, 80) }}
          </p>
          <div class="flex items-center gap-3 mt-1 text-xs text-zinc-600">
            <span>{{ paper.venue || '预印本' }}</span>
            <span>可信度 {{ paper.credibility_score?.toFixed(1) || '-' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
