<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

interface Sub {
  id: string
  query_text?: string
  researcher_name?: string
  ai_keywords: string[]
  status: string
  created_at: string
}

const topicSubs = ref<Sub[]>([])
const researcherSubs = ref<Sub[]>([])
const loading = ref(true)

onMounted(async () => {
  await loadSubs()
})

async function loadSubs() {
  loading.value = true
  try {
    const [t, r] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
    ])
    topicSubs.value = t.data
    researcherSubs.value = r.data
  } finally {
    loading.value = false
  }
}

async function toggleTopic(sub: Sub) {
  const newStatus = sub.status === 'active' ? 'paused' : 'active'
  await api.patch(`/subscriptions/topics/${sub.id}`, { status: newStatus })
  sub.status = newStatus
}

async function deleteTopic(id: string) {
  if (!confirm('确定删除这个订阅？')) return
  await api.delete(`/subscriptions/topics/${id}`)
  topicSubs.value = topicSubs.value.filter((s) => s.id !== id)
}

async function toggleResearcher(sub: Sub) {
  const newStatus = sub.status === 'active' ? 'paused' : 'active'
  await api.patch(`/subscriptions/researchers/${sub.id}`, { status: newStatus })
  sub.status = newStatus
}

async function deleteResearcher(id: string) {
  if (!confirm('确定删除这个追踪？')) return
  await api.delete(`/subscriptions/researchers/${id}`)
  researcherSubs.value = researcherSubs.value.filter((s) => s.id !== id)
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold text-white mb-8">订阅管理</h1>

    <!-- Topic -->
    <section class="mb-10">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📚 领域订阅</h2>
      <div v-if="topicSubs.length === 0" class="text-zinc-500 text-sm">暂无领域订阅</div>
      <div v-for="sub in topicSubs" :key="sub.id"
        class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg mb-3">
        <div class="flex items-center justify-between mb-2">
          <span class="text-white font-medium">{{ sub.query_text }}</span>
          <div class="flex items-center gap-2">
            <button @click="toggleTopic(sub)"
              :class="sub.status === 'active' ? 'text-green-400 hover:text-green-300' : 'text-zinc-500 hover:text-zinc-400'"
              class="text-xs transition">
              {{ sub.status === 'active' ? '活跃' : '已暂停' }}
            </button>
            <button @click="deleteTopic(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 transition">删除</button>
          </div>
        </div>
        <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1">
          <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded">
            {{ kw }}
          </span>
        </div>
      </div>
    </section>

    <!-- Researcher -->
    <section>
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">👤 研究者追踪</h2>
      <div v-if="researcherSubs.length === 0" class="text-zinc-500 text-sm">暂无研究者追踪</div>
      <div v-for="sub in researcherSubs" :key="sub.id"
        class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg mb-3">
        <div class="flex items-center justify-between">
          <span class="text-white font-medium">{{ sub.researcher_name }}</span>
          <div class="flex items-center gap-2">
            <button @click="toggleResearcher(sub)"
              :class="sub.status === 'active' ? 'text-green-400 hover:text-green-300' : 'text-zinc-500 hover:text-zinc-400'"
              class="text-xs transition">
              {{ sub.status === 'active' ? '活跃' : '已暂停' }}
            </button>
            <button @click="deleteResearcher(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 transition">删除</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
