<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { auth, fetchUser } from '../stores/auth'
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
const error = ref('')
const running = ref(false)
const runStatus = ref('')
const runProgress = ref(0)

// Tag editing
const editingTag = ref<string | null>(null)
const newTag = ref('')

onMounted(async () => {
  if (!auth.user && auth.token) {
    try {
      await fetchUser()
    } catch {
      router.push('/login')
      return
    }
  }
  if (!auth.token) {
    router.push('/login')
    return
  }
  await loadData()
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [t, r, b] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
      api.get('/pipeline/briefs'),
    ])
    topicSubs.value = t.data
    researcherSubs.value = r.data
    briefs.value = b.data
  } catch (e: any) {
    if (e.response?.status === 401) {
      router.push('/login')
      return
    }
    error.value = '数据加载失败'
  } finally {
    loading.value = false
  }
}

async function runPipeline() {
  running.value = true
  runStatus.value = '正在搜索论文...'
  runProgress.value = 10
  try {
    await api.post('/pipeline/run')
    runStatus.value = '正在评分和生成简报...'
    runProgress.value = 50
    for (let i = 0; i < 10; i++) {
      await new Promise(r => setTimeout(r, 3000))
      runProgress.value = 50 + i * 5
      const { data } = await api.get('/pipeline/briefs')
      if (data.length > briefs.value.length) {
        briefs.value = data
        runStatus.value = '完成！'
        runProgress.value = 100
        break
      }
      runStatus.value = `等待中... (${(i + 1) * 3}s)`
    }
    if (briefs.value.length === 0) {
      const { data } = await api.get('/pipeline/briefs')
      briefs.value = data
      runStatus.value = briefs.value.length > 0 ? '完成！' : '未找到新论文，请确认订阅有关键词'
    }
  } catch {
    runStatus.value = 'Pipeline 执行失败'
  } finally {
    running.value = false
    setTimeout(() => { runStatus.value = ''; runProgress.value = 0 }, 5000)
  }
}

function goOnboarding() {
  router.push('/onboarding')
}

async function deleteTopic(id: string) {
  const topic = topicSubs.value.find(s => s.id === id)
  if (!topic || !topic.query_text) return
  if (!confirm('确定删除领域「' + topic.query_text + '」？')) return

  // Find researchers tagged with this domain
  const domainTag = topic.query_text
  const linkedResearchers = researcherSubs.value.filter(
    r => r.ai_keywords.includes(domainTag)
  )

  await api.delete(`/subscriptions/topics/${id}`)
  topicSubs.value = topicSubs.value.filter(s => s.id !== id)

  if (linkedResearchers.length > 0) {
    const shouldDelete = confirm(
      `该领域下有 ${linkedResearchers.length} 位研究者（${linkedResearchers.map(r => r.researcher_name).slice(0, 3).join('、')}${linkedResearchers.length > 3 ? '等' : ''}）。\n\n是否同时删除这些研究者？\n\n确定=一并删除 | 取消=保留研究者`
    )
    if (shouldDelete) {
      for (const r of linkedResearchers) {
        await api.delete(`/subscriptions/researchers/${r.id}`)
      }
      researcherSubs.value = researcherSubs.value.filter(
        r => !linkedResearchers.includes(r)
      )
    }
  }
}

async function deleteResearcher(id: string) {
  if (!confirm('确定删除这个追踪？')) return
  await api.delete(`/subscriptions/researchers/${id}`)
  researcherSubs.value = researcherSubs.value.filter(s => s.id !== id)
}

async function deleteBrief(id: string) {
  if (!confirm('确定删除这份简报？')) return
  await api.delete(`/pipeline/briefs/${id}`)
  briefs.value = briefs.value.filter(b => b.id !== id)
}

function getLatestBriefDate(subId: string): string | null {
  const subBriefs = briefs.value.filter(b => b.subscription_id === subId)
  if (subBriefs.length === 0) return null
  return subBriefs.sort((a, b) => b.date.localeCompare(a.date))[0].date
}

// ── Tag management ──

function startEditTag(subId: string) {
  editingTag.value = subId
  newTag.value = ''
  nextTick(() => {
    const input = document.querySelector<HTMLInputElement>(`[data-tag-input="${subId}"]`)
    input?.focus()
  })
}

async function addTag(sub: Sub) {
  const tag = newTag.value.trim()
  if (!tag) return
  const updated = [...sub.ai_keywords, tag]
  await api.patch(`/subscriptions/researchers/${sub.id}`, { ai_keywords: updated })
  sub.ai_keywords = updated
  newTag.value = ''
}

async function removeTag(sub: Sub, tag: string) {
  const updated = sub.ai_keywords.filter(t => t !== tag)
  await api.patch(`/subscriptions/researchers/${sub.id}`, { ai_keywords: updated })
  sub.ai_keywords = updated
}

function doneEditing() {
  editingTag.value = null
  newTag.value = ''
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-10">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-white">控制台</h1>
      <div class="flex items-center gap-3">
        <button @click="runPipeline()" :disabled="running"
          class="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm rounded-lg transition">
          {{ running ? '运行中...' : '运行 Pipeline' }}
        </button>
        <button @click="goOnboarding"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition">
          + 新建订阅
        </button>
      </div>
    </div>

    <!-- Pipeline progress -->
    <div v-if="runStatus" class="mb-6 p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm text-zinc-300">{{ runStatus }}</span>
        <span class="text-xs text-zinc-500">{{ runProgress }}%</span>
      </div>
      <div class="w-full bg-zinc-800 rounded-full h-1.5">
        <div class="bg-green-500 h-1.5 rounded-full transition-all duration-500" :style="{ width: runProgress + '%' }"></div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error"
      class="p-4 bg-red-950/30 border border-red-900/30 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-3">
      <span>{{ error }}</span>
      <button @click="loadData" class="text-red-300 hover:text-red-200 underline text-xs">重试</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-20">
      <div class="inline-block w-6 h-6 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin mb-3"></div>
      <p class="text-zinc-500 text-sm">加载中...</p>
    </div>

    <template v-if="!loading && !error">
      <!-- Empty state -->
      <div v-if="topicSubs.length === 0 && researcherSubs.length === 0"
        class="text-center py-20">
        <p class="text-zinc-500 text-lg mb-4">还没有任何订阅</p>
        <p class="text-zinc-600 mb-6">创建你的第一个订阅，开始追踪研究动态</p>
        <button @click="goOnboarding"
          class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition">
          开始引导
        </button>
      </div>

      <!-- Topic subscriptions -->
      <section v-if="topicSubs.length > 0" class="mb-6">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">领域订阅 ({{ topicSubs.length }})</h2>
        <div class="grid gap-2">
          <div v-for="sub in topicSubs" :key="sub.id"
            class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg group">
            <div class="flex items-center justify-between">
              <span class="text-white text-sm">{{ sub.query_text }}</span>
              <div class="flex items-center gap-2">
                <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
                  {{ sub.status === 'active' ? '活跃' : '暂停' }}
                </span>
                <button @click="deleteTopic(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
              </div>
            </div>
            <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1 mt-1.5">
              <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-blue-900/30 text-blue-300 text-xs rounded">
                {{ kw }}
              </span>
            </div>
            <div class="text-xs text-zinc-600 mt-1">
              创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}
              <span v-if="getLatestBriefDate(sub.id)" class="ml-3">最新论文 {{ getLatestBriefDate(sub.id) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Researcher subscriptions -->
      <section v-if="researcherSubs.length > 0" class="mb-8">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">研究者追踪 ({{ researcherSubs.length }})</h2>
        <div class="grid gap-2">
          <div v-for="sub in researcherSubs" :key="sub.id"
            class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg group">
            <div class="flex items-center justify-between">
              <span class="text-white text-sm">{{ sub.researcher_name }}</span>
              <div class="flex items-center gap-2">
                <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
                  {{ sub.status === 'active' ? '活跃' : '暂停' }}
                </span>
                <button @click="deleteResearcher(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
              </div>
            </div>
            <!-- Tags -->
            <div class="flex flex-wrap items-center gap-1 mt-1.5">
              <span v-for="tag in sub.ai_keywords" :key="tag"
                class="px-1.5 py-0.5 bg-blue-900/40 text-blue-300 text-xs rounded cursor-pointer hover:bg-red-900/40 hover:text-red-300 transition"
                @click="removeTag(sub, tag)" title="点击删除标签">
                {{ tag }} ×
              </span>
              <template v-if="editingTag === sub.id">
                <input v-model="newTag" @keyup.enter="addTag(sub)" @keyup.escape="doneEditing()" @blur="doneEditing()"
                  :data-tag-input="sub.id" placeholder="标签..."
                  class="w-16 px-1 py-0.5 bg-zinc-800 border border-zinc-600 rounded text-xs text-white focus:outline-none focus:border-blue-500" />
              </template>
              <button v-else @click="startEditTag(sub.id)"
                class="px-1 py-0.5 border border-dashed border-zinc-700 text-zinc-600 text-xs rounded hover:border-zinc-500 hover:text-zinc-400 transition">
                + 标签
              </button>
            </div>
            <div class="text-xs text-zinc-600 mt-1">
              创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}
              <span v-if="getLatestBriefDate(sub.id)" class="ml-3">最新论文 {{ getLatestBriefDate(sub.id) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Recent Briefs -->
      <section v-if="briefs.length > 0">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">最新简报</h2>
        <div class="grid gap-2">
          <div v-for="brief in briefs.slice(0, 10)" :key="brief.id"
            class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer flex items-center justify-between group"
            @click="router.push(`/briefs/${brief.id}`)">
            <div>
              <span class="text-white text-sm">{{ brief.date }}</span>
              <span class="text-xs text-zinc-500 ml-2">{{ brief.subscription_type === 'researcher' ? '研究者' : '领域' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs text-zinc-500">{{ brief.papers?.length || 0 }} 篇</span>
              <button @click.stop="deleteBrief(brief.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
            </div>
          </div>
        </div>
      </section>

      <div v-if="topicSubs.length > 0 && briefs.length === 0 && !runStatus" class="text-center py-10">
        <p class="text-zinc-500 text-sm mb-2">还没有简报</p>
        <p class="text-zinc-600 text-xs">点击上方「运行 Pipeline」生成第一份每日简报</p>
      </div>
    </template>
  </div>
</template>
