<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

interface Sub {
  id: string
  query_text?: string
  researcher_name?: string
  status: string
  created_at: string
}

interface Brief {
  id: string
  subscription_type: string
  date: string
  papers: any[]
}

const router = useRouter()
const topicSubs = ref<Sub[]>([])
const researcherSubs = ref<Sub[]>([])
const briefs = ref<Brief[]>([])
const loading = ref(true)
const running = ref(false)

onMounted(async () => {
  try {
    const [t, r, b] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
      api.get('/pipeline/briefs'),
    ])
    topicSubs.value = t.data
    researcherSubs.value = r.data
    briefs.value = b.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function runPipeline() {
  running.value = true
  try {
    await api.post('/pipeline/run')
    // Brief wait then reload briefs
    setTimeout(async () => {
      const { data } = await api.get('/pipeline/briefs')
      briefs.value = data
      running.value = false
    }, 3000)
  } catch {
    running.value = false
  }
}

function goOnboarding() {
  router.push('/onboarding')
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-10">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-white">控制台</h1>
      <div class="flex items-center gap-3">
        <button @click="runPipeline" :disabled="running"
          class="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm rounded-lg transition">
          {{ running ? '运行中...' : '⚡ 运行 Pipeline' }}
        </button>
        <button @click="goOnboarding"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition">
          + 新建订阅
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && topicSubs.length === 0 && researcherSubs.length === 0"
      class="text-center py-20">
      <p class="text-zinc-500 text-lg mb-4">还没有任何订阅</p>
      <p class="text-zinc-600 mb-6">创建你的第一个订阅，开始追踪研究动态</p>
      <button @click="goOnboarding"
        class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition">
        开始引导
      </button>
    </div>

    <!-- Subscriptions -->
    <section v-if="topicSubs.length > 0" class="mb-6">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📚 领域订阅 ({{ topicSubs.length }})</h2>
      <div class="grid gap-2">
        <div v-for="sub in topicSubs" :key="sub.id"
          class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between">
          <span class="text-white text-sm">{{ sub.query_text }}</span>
          <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
            {{ sub.status === 'active' ? '活跃' : '暂停' }}
          </span>
        </div>
      </div>
    </section>

    <section v-if="researcherSubs.length > 0" class="mb-8">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">👤 研究者追踪 ({{ researcherSubs.length }})</h2>
      <div class="grid gap-2">
        <div v-for="sub in researcherSubs" :key="sub.id"
          class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between">
          <span class="text-white text-sm">{{ sub.researcher_name }}</span>
          <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
            {{ sub.status === 'active' ? '活跃' : '暂停' }}
          </span>
        </div>
      </div>
    </section>

    <!-- Recent Briefs -->
    <section v-if="briefs.length > 0">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📰 最新简报</h2>
      <div class="grid gap-2">
        <div v-for="brief in briefs.slice(0, 10)" :key="brief.id"
          class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer flex items-center justify-between"
          @click="router.push(`/briefs/${brief.id}`)">
          <div>
            <span class="text-white text-sm">{{ brief.date }}</span>
            <span class="text-xs text-zinc-500 ml-2">{{ brief.subscription_type === 'researcher' ? '👤' : '📚' }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-zinc-500">{{ brief.papers?.length || 0 }} 篇</span>
            <span class="text-zinc-600 text-xs">→</span>
          </div>
        </div>
      </div>
    </section>

    <div v-if="!loading && topicSubs.length > 0 && briefs.length === 0" class="text-center py-10">
      <p class="text-zinc-500 text-sm mb-2">还没有简报</p>
      <p class="text-zinc-600 text-xs">点击上方「运行 Pipeline」生成第一份每日简报</p>
    </div>
  </div>
</template>
