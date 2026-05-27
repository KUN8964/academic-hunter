<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

// Selection
const selectedSubs = ref<Set<string>>(new Set())

// Running state
const runningSubs = ref<Set<string>>(new Set())
const subRunStatus = ref<Record<string, string>>({})

// Collapse
const showAllResearchers = ref(false)

// Tag editing
const editingTag = ref<string | null>(null)
const newTag = ref('')

onMounted(async () => {
  if (!auth.user && auth.token) {
    try { await fetchUser() } catch { router.push('/login'); return }
  }
  if (!auth.token) { router.push('/login'); return }
  await loadAll()
})

async function loadAll() {
  loading.value = true; error.value = ''
  try {
    const [t, r, b] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
      api.get('/pipeline/briefs'),
    ])
    topicSubs.value = t.data; researcherSubs.value = r.data; briefs.value = b.data
  } catch (e: any) {
    if (e.response?.status === 401) { router.push('/login'); return }
    error.value = '加载失败，请刷新重试'
  } finally { loading.value = false }
}

function toggleSelect(subId: string) {
  const next = new Set(selectedSubs.value)
  if (next.has(subId)) next.delete(subId)
  else next.add(subId)
  selectedSubs.value = next
}

async function runSelected() {
  const toRun = [...selectedSubs.value]
  if (toRun.length === 0) return
  for (const subId of toRun) {
    const isTopic = topicSubs.value.some(s => s.id === subId)
    const type = isTopic ? 'topic' : 'researcher'
    runningSubs.value.add(subId)
    subRunStatus.value[subId] = '搜索中...'
    try {
      const endpoint = type === 'topic' ? `/pipeline/run/topic/${subId}` : `/pipeline/run/researcher/${subId}`
      const { data } = await api.post(endpoint)
      if (data.brief) {
        subRunStatus.value[subId] = `完成！${data.brief.papers?.length || 0} 篇`
        const b = await api.get('/pipeline/briefs'); briefs.value = b.data
      } else {
        subRunStatus.value[subId] = data.message || '未找到新论文'
      }
    } catch (e: any) {
      subRunStatus.value[subId] = '失败'
    } finally {
      runningSubs.value.delete(subId)
      setTimeout(() => { delete subRunStatus.value[subId] }, 6000)
    }
  }
}

async function toggleTopic(sub: Sub) {
  const newStatus = sub.status === 'active' ? 'paused' : 'active'
  await api.patch(`/subscriptions/topics/${sub.id}`, { status: newStatus })
  sub.status = newStatus
}

async function deleteTopic(id: string) {
  const topic = topicSubs.value.find((s: Sub) => s.id === id)
  if (!topic?.query_text) return
  if (!confirm('确定删除领域「' + topic.query_text + '」？')) return
  const linkedResearchers = researcherSubs.value.filter((r: Sub) => r.ai_keywords.includes(topic.query_text!))
  await api.delete(`/subscriptions/topics/${id}`)
  topicSubs.value = topicSubs.value.filter((s: Sub) => s.id !== id)
  selectedSubs.value.delete(id)
  if (linkedResearchers.length > 0) {
    const shouldDelete = confirm('该领域下有 ' + linkedResearchers.length + ' 位研究者（' + linkedResearchers.map(r => r.researcher_name).slice(0, 3).join('、') + (linkedResearchers.length > 3 ? '等' : '') + '）。\n\n是否同时删除这些研究者？\n\n确定=一并删除 | 取消=保留研究者')
    if (shouldDelete) {
      for (const r of linkedResearchers) { await api.delete(`/subscriptions/researchers/${r.id}`) }
      researcherSubs.value = researcherSubs.value.filter((r: Sub) => !linkedResearchers.includes(r))
    }
  }
}

async function toggleResearcher(sub: Sub) {
  const newStatus = sub.status === 'active' ? 'paused' : 'active'
  await api.patch(`/subscriptions/researchers/${sub.id}`, { status: newStatus })
  sub.status = newStatus
}

async function deleteResearcher(id: string) {
  if (!confirm('确定删除这个追踪？')) return
  await api.delete(`/subscriptions/researchers/${id}`)
  researcherSubs.value = researcherSubs.value.filter((s: Sub) => s.id !== id)
  selectedSubs.value.delete(id)
}

async function deleteBrief(id: string) {
  if (!confirm('确定删除这份简报？')) return
  await api.delete(`/pipeline/briefs/${id}`)
  briefs.value = briefs.value.filter(b => b.id !== id)
}

// Tag management
function startEditTag(subId: string) { editingTag.value = subId; newTag.value = '' }
async function addTag(sub: Sub) {
  const tag = newTag.value.trim(); if (!tag) return
  const updated = [...sub.ai_keywords, tag]
  await api.patch(`/subscriptions/researchers/${sub.id}`, { ai_keywords: updated })
  sub.ai_keywords = updated; newTag.value = ''
}
async function removeTag(sub: Sub, tag: string) {
  const updated = sub.ai_keywords.filter(t => t !== tag)
  await api.patch(`/subscriptions/researchers/${sub.id}`, { ai_keywords: updated })
  sub.ai_keywords = updated
}
function doneEditing() { editingTag.value = null; newTag.value = '' }

function getSubName(brief: Brief): string {
  const topic = topicSubs.value.find(s => s.id === brief.subscription_id)
  if (topic) return topic.query_text || '(未命名)'
  const researcher = researcherSubs.value.find(s => s.id === brief.subscription_id)
  if (researcher) return researcher.researcher_name || '(未命名)'
  return '(已删除的订阅)'
}

function getLatestBriefDate(subId: string): string | null {
  const subBriefs = briefs.value.filter(b => b.subscription_id === subId)
  if (subBriefs.length === 0) return null
  return subBriefs.sort((a, b) => b.date.localeCompare(a.date))[0].date
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">订阅管理</h1>
      <button @click="runSelected" :disabled="selectedSubs.size === 0 || runningSubs.size > 0"
        class="px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-30"
        :class="selectedSubs.size > 0 ? 'bg-green-600 hover:bg-green-500 text-white cursor-pointer' : 'bg-zinc-800 text-zinc-500'">
        {{ runningSubs.size > 0 ? `运行中 (${runningSubs.size})...` : `立即运行 (${selectedSubs.size})` }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-4 bg-red-950/30 border border-red-900/30 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-3">
      <span>{{ error }}</span>
      <button @click="loadAll" class="text-red-300 hover:text-red-200 underline text-xs">重试</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block w-6 h-6 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin mb-3"></div>
      <p class="text-zinc-500 text-sm">加载中...</p>
    </div>

    <template v-if="!loading && !error">
      <!-- Topic -->
      <section class="mb-10">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">
          领域订阅 <span class="text-zinc-600 text-sm">({{ topicSubs.length }})</span>
        </h2>
        <div v-if="topicSubs.length === 0" class="text-zinc-500 text-sm">
          暂无领域订阅，前往 <router-link to="/onboarding" class="text-blue-400 hover:underline">引导页</router-link> 创建
        </div>
        <div v-for="sub in topicSubs" :key="sub.id"
          @click="toggleSelect(sub.id)"
          class="p-4 rounded-lg border cursor-pointer transition mb-3 group"
          :class="selectedSubs.has(sub.id) ? 'bg-blue-950/30 border-blue-700' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span :class="selectedSubs.has(sub.id) ? 'text-blue-400' : 'text-zinc-700'" class="text-sm">●</span>
              <span class="text-white font-medium">{{ sub.query_text }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="subRunStatus[sub.id]" class="text-xs"
                :class="subRunStatus[sub.id].startsWith('完成') ? 'text-green-400' : subRunStatus[sub.id] === '失败' ? 'text-red-400' : 'text-blue-400'">
                {{ subRunStatus[sub.id] }}
              </span>
              <span v-if="runningSubs.has(sub.id)" class="inline-block w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin"></span>
              <button @click.stop="toggleTopic(sub)"
                :class="sub.status === 'active' ? 'text-green-400 hover:text-green-300' : 'text-zinc-500 hover:text-zinc-400'"
                class="text-xs transition">{{ sub.status === 'active' ? '活跃' : '已暂停' }}</button>
              <button @click.stop="deleteTopic(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 transition">删除</button>
            </div>
          </div>
          <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1 mb-2">
            <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded">{{ kw }}</span>
          </div>
          <div class="text-xs text-zinc-600 mt-2">创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}</div>
        </div>
      </section>

      <!-- Researcher -->
      <section class="mb-10">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4"
          @click="showAllResearchers = !showAllResearchers"
          style="cursor:pointer">
          研究者追踪 <span class="text-zinc-600 text-sm">({{ researcherSubs.length }})</span>
          <span v-if="researcherSubs.length > 5" class="text-xs text-zinc-500 ml-1">{{ showAllResearchers ? '▲ 收起' : '▼ 展开' }}</span>
        </h2>
        <div v-if="researcherSubs.length === 0 && !loading" class="text-zinc-500 text-sm">暂无研究者追踪</div>
        <template v-for="sub in (showAllResearchers ? researcherSubs : researcherSubs.slice(0, 5))" :key="sub.id">
          <div
            @click="toggleSelect(sub.id)"
            class="p-4 rounded-lg border cursor-pointer transition mb-3 group"
            :class="selectedSubs.has(sub.id) ? 'bg-blue-950/30 border-blue-700' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'"
          >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span :class="selectedSubs.has(sub.id) ? 'text-blue-400' : 'text-zinc-700'" class="text-sm">●</span>
              <span class="text-white font-medium">{{ sub.researcher_name }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="subRunStatus[sub.id]" class="text-xs"
                :class="subRunStatus[sub.id].startsWith('完成') ? 'text-green-400' : subRunStatus[sub.id] === '失败' ? 'text-red-400' : 'text-blue-400'">
                {{ subRunStatus[sub.id] }}
              </span>
              <span v-if="runningSubs.has(sub.id)" class="inline-block w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin"></span>
              <button @click.stop="toggleResearcher(sub)"
                :class="sub.status === 'active' ? 'text-green-400 hover:text-green-300' : 'text-zinc-500 hover:text-zinc-400'"
                class="text-xs transition">{{ sub.status === 'active' ? '活跃' : '已暂停' }}</button>
              <button @click.stop="deleteResearcher(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 transition">删除</button>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-1 mt-2">
            <span v-for="tag in sub.ai_keywords" :key="tag"
              class="px-1.5 py-0.5 bg-blue-900/40 text-blue-300 text-xs rounded cursor-pointer hover:bg-red-900/40 hover:text-red-300 transition"
              @click.stop="removeTag(sub, tag)" title="点击删除标签">{{ tag }} ×</span>
            <template v-if="editingTag === sub.id">
              <input v-model="newTag" @keyup.enter="addTag(sub)" @keyup.escape="doneEditing()" @blur="doneEditing()"
                @click.stop placeholder="领域标签..."
                class="w-20 px-1.5 py-0.5 bg-zinc-800 border border-zinc-600 rounded text-xs text-white focus:outline-none focus:border-blue-500" />
            </template>
            <button v-else @click.stop="startEditTag(sub.id)"
              class="px-1.5 py-0.5 border border-dashed border-zinc-700 text-zinc-600 text-xs rounded hover:border-zinc-500 hover:text-zinc-400 transition">+ 标签</button>
          </div>
          <div class="text-xs text-zinc-600 mt-2 flex gap-4">
            <span>创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}</span>
            <span v-if="getLatestBriefDate(sub.id)">最新论文 {{ getLatestBriefDate(sub.id) }}</span>
          </div>
          </div>
          </template>
      </section>

      <!-- Briefs -->
      <section>
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">
          每日简报 <span class="text-zinc-600 text-sm">({{ briefs.length }})</span>
        </h2>
        <div v-if="briefs.length === 0 && !loading" class="text-zinc-500 text-sm">
          暂无简报。选中领域/研究者，点击上方「立即运行」生成。
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
    </template>
  </div>
</template>
