<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

interface Sub {
  id: string
  query_text?: string
  researcher_name?: string
  ai_keywords: string[]
  status: string
  created_at: string
}

interface Brief {
  id: string
  subscription_type: string
  subscription_id: string
  date: string
  papers: any[]
}

const router = useRouter()
const topicSubs = ref<Sub[]>([])
const researcherSubs = ref<Sub[]>([])
const briefs = ref<Brief[]>([])
const loading = ref(true)
const running = ref(false)
const runMsg = ref('')
const runProgress = ref(0)

onMounted(async () => {
  await loadAll()
})

async function loadAll() {
  loading.value = true
  try {
    const [t, r, b] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
      api.get('/pipeline/briefs'),
    ])
    topicSubs.value = t.data
    researcherSubs.value = r.data
    briefs.value = b.data
  } finally {
    loading.value = false
  }
}

async function triggerPipeline() {
  running.value = true
  runMsg.value = '正在搜索 arXiv + Semantic Scholar...'
  runProgress.value = 10
  try {
    await api.post('/pipeline/run')
    runMsg.value = '正在评分和生成简报...'
    runProgress.value = 50
    const prevCount = briefs.value.length
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 3000))
      runProgress.value = 50 + i * 5
      const { data } = await api.get('/pipeline/briefs')
      if (data.length > prevCount) {
        briefs.value = data
        runMsg.value = `完成！新增 ${data.length - prevCount} 份简报`
        runProgress.value = 100
        break
      }
      runMsg.value = `等待中... (${(i + 1) * 3}s)`
    }
    if (briefs.value.length === prevCount) {
      const { data } = await api.get('/pipeline/briefs')
      briefs.value = data
      runMsg.value = briefs.value.length > prevCount ? '完成！' : '未找到新论文，请确认订阅有关键词'
    }
  } catch (e: any) {
    runMsg.value = '启动失败: ' + (e.response?.data?.detail || '未知错误')
  }
  running.value = false
  setTimeout(() => { runMsg.value = ''; runProgress.value = 0 }, 5000)
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

async function deleteBrief(id: string) {
  if (!confirm('确定删除这份简报？')) return
  await api.delete(`/pipeline/briefs/${id}`)
  briefs.value = briefs.value.filter(b => b.id !== id)
}

function getSubName(brief: Brief): string {
  const topic = topicSubs.value.find(s => s.id === brief.subscription_id)
  if (topic) return topic.query_text || '(未命名)'
  const researcher = researcherSubs.value.find(s => s.id === brief.subscription_id)
  if (researcher) return researcher.researcher_name || '(未命名)'
  return '(已删除的订阅)'
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">订阅管理</h1>
      <button @click="triggerPipeline" :disabled="running"
        class="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm rounded-lg transition">
        {{ running ? '启动中...' : '⚡ 立即运行 Pipeline' }}
      </button>
    </div>

    <p v-if="runMsg" class="text-sm text-green-400 mb-4">
      {{ runMsg }}
      <span v-if="runProgress > 0 && runProgress < 100" class="text-zinc-500 ml-2">{{ runProgress }}%</span>
    </p>

    <!-- Topic -->
    <section class="mb-10">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📚 领域订阅 <span class="text-zinc-600 text-sm">({{ topicSubs.length }})</span></h2>
      <div v-if="topicSubs.length === 0 && !loading" class="text-zinc-500 text-sm">暂无领域订阅，前往 <router-link to="/onboarding" class="text-blue-400">引导页</router-link> 创建</div>
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
        <!-- AI keywords -->
        <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1 mb-2">
          <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded">
            {{ kw }}
          </span>
        </div>
        <!-- Link to latest briefs -->
        <div class="text-xs text-zinc-600 mt-2">
          创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}
        </div>
      </div>
    </section>

    <!-- Researcher -->
    <section class="mb-10">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">👤 研究者追踪 <span class="text-zinc-600 text-sm">({{ researcherSubs.length }})</span></h2>
      <div v-if="researcherSubs.length === 0 && !loading" class="text-zinc-500 text-sm">暂无研究者追踪</div>
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
        <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1 mt-2">
          <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded">
            {{ kw }}
          </span>
        </div>
      </div>
    </section>

    <!-- Daily Briefs -->
    <section>
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📰 每日简报 <span class="text-zinc-600 text-sm">({{ briefs.length }})</span></h2>
      <div v-if="briefs.length === 0 && !loading" class="text-zinc-500 text-sm">
        暂无简报。点击上方「立即运行 Pipeline」生成第一份简报。
      </div>
      <div v-for="brief in briefs" :key="brief.id"
        class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg mb-3 hover:border-zinc-700 transition cursor-pointer group"
        @click="router.push(`/briefs/${brief.id}`)">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-white text-sm">{{ brief.date }}</span>
            <span class="text-zinc-500 text-xs ml-2">{{ getSubName(brief) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-zinc-500">{{ brief.papers?.length || 0 }} 篇论文</span>
            <button @click.stop="deleteBrief(brief.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
