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

// Selection
const selectedSubs = ref<Set<string>>(new Set())

// Running state
const runningSubs = ref<Set<string>>(new Set())
const subRunStatus = ref<Record<string, string>>({})

// Researcher collapse
const showAllResearchers = ref(false)

// Tag editing
const editingTag = ref<string | null>(null)
const newTag = ref('')

onMounted(async () => {
  if (!auth.user && auth.token) {
    try { await fetchUser() } catch { router.push('/login'); return }
  }
  if (!auth.token) { router.push('/login'); return }
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
    if (e.response?.status === 401) { router.push('/login'); return }
    error.value = '数据加载失败'
  } finally {
    loading.value = false
  }
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
      const endpoint = type === 'topic'
        ? `/pipeline/run/topic/${subId}`
        : `/pipeline/run/researcher/${subId}`
      const { data } = await api.post(endpoint)
      if (data.brief) {
        subRunStatus.value[subId] = `完成！${data.brief.papers?.length || 0} 篇`
        const b = await api.get('/pipeline/briefs')
        briefs.value = b.data
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

function goOnboarding() { router.push('/onboarding') }

async function deleteTopic(id: string) {
  const topic = topicSubs.value.find(s => s.id === id)
  if (!topic?.query_text) return
  if (!confirm('确定删除领域「' + topic.query_text + '」？')) return
  const linkedResearchers = researcherSubs.value.filter(r => r.ai_keywords.includes(topic.query_text!))
  await api.delete(`/subscriptions/topics/${id}`)
  topicSubs.value = topicSubs.value.filter(s => s.id !== id)
  selectedSubs.value.delete(id)
  if (linkedResearchers.length > 0) {
    const shouldDelete = confirm(`该领域下有 ${linkedResearchers.length} 位研究者，是否同时删除？\n确定=一并删除 | 取消=保留研究者`)
    if (shouldDelete) {
      for (const r of linkedResearchers) {
        await api.delete(`/subscriptions/researchers/${r.id}`)
      }
      researcherSubs.value = researcherSubs.value.filter(r => !linkedResearchers.includes(r))
    }
  }
}

async function deleteResearcher(id: string) {
  if (!confirm('确定删除这个追踪？')) return
  await api.delete(`/subscriptions/researchers/${id}`)
  researcherSubs.value = researcherSubs.value.filter(s => s.id !== id)
  selectedSubs.value.delete(id)
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

function startEditTag(subId: string) { editingTag.value = subId; newTag.value = ''; nextTick(() => { document.querySelector<HTMLInputElement>(`[data-tag-input="${subId}"]`)?.focus() }) }
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
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-10">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-white">控制台</h1>
      <div class="flex items-center gap-3">
        <button @click="runSelected" :disabled="selectedSubs.size === 0 || runningSubs.size > 0"
          class="px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-30"
          :class="selectedSubs.size > 0 ? 'bg-green-600 hover:bg-green-500 text-white cursor-pointer' : 'bg-zinc-800 text-zinc-500'">
          {{ runningSubs.size > 0 ? `运行中 (${runningSubs.size})...` : `立即运行 (${selectedSubs.size})` }}
        </button>
        <button @click="goOnboarding"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition">
          + 新建订阅
        </button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-4 bg-red-950/30 border border-red-900/30 rounded-lg text-red-400 text-sm mb-6 flex items-center gap-3">
      <span>{{ error }}</span>
      <button @click="loadData" class="text-red-300 hover:text-red-200 underline text-xs">重试</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-20">
      <div class="inline-block w-6 h-6 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin mb-3"></div>
      <p class="text-zinc-500 text-sm">加载中...</p>
    </div>

    <template v-if="!loading && !error">
      <!-- Empty -->
      <div v-if="topicSubs.length === 0 && researcherSubs.length === 0" class="text-center py-20">
        <p class="text-zinc-500 text-lg mb-4">还没有任何订阅</p>
        <p class="text-zinc-600 mb-6">创建你的第一个订阅，开始追踪研究动态</p>
        <button @click="goOnboarding" class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition">开始引导</button>
      </div>

      <!-- Topic subscriptions -->
      <section v-if="topicSubs.length > 0" class="mb-6">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">领域订阅 ({{ topicSubs.length }})</h2>
        <div class="grid gap-2">
          <div v-for="sub in topicSubs" :key="sub.id"
            @click="toggleSelect(sub.id)"
            class="p-3 rounded-lg border cursor-pointer transition group"
            :class="selectedSubs.has(sub.id) ? 'bg-blue-950/30 border-blue-700' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="selectedSubs.has(sub.id) ? 'text-blue-400' : 'text-zinc-700'" class="text-sm">●</span>
                <span class="text-white text-sm">{{ sub.query_text }}</span>
              </div>
              <div class="flex items-center gap-2">
                <!-- Run status -->
                <span v-if="subRunStatus[sub.id]" class="text-xs"
                  :class="subRunStatus[sub.id].startsWith('完成') ? 'text-green-400' : subRunStatus[sub.id] === '失败' ? 'text-red-400' : 'text-blue-400'">
                  {{ subRunStatus[sub.id] }}
                </span>
                <span v-if="runningSubs.has(sub.id)" class="inline-block w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin"></span>
                <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">{{ sub.status === 'active' ? '活跃' : '暂停' }}</span>
                <button @click.stop="deleteTopic(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
              </div>
            </div>
            <div v-if="sub.ai_keywords?.length" class="flex flex-wrap gap-1 mt-1.5">
              <span v-for="kw in sub.ai_keywords" :key="kw" class="px-1.5 py-0.5 bg-blue-900/30 text-blue-300 text-xs rounded">{{ kw }}</span>
            </div>
            <div class="text-xs text-zinc-600 mt-1">
              创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}
              <span v-if="getLatestBriefDate(sub.id)" class="ml-3">最新论文 {{ getLatestBriefDate(sub.id) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Researcher subscriptions (collapsed) -->
      <section v-if="researcherSubs.length > 0" class="mb-8">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4"
          @click="showAllResearchers = !showAllResearchers"
          style="cursor:pointer">
          研究者追踪 ({{ researcherSubs.length }})
          <span class="text-xs text-zinc-500 ml-1">{{ showAllResearchers ? '▲ 收起' : '▼ 展开' }}</span>
        </h2>
        <div class="grid gap-2">
          <template v-for="sub in (showAllResearchers ? researcherSubs : researcherSubs.slice(0, 5))" :key="sub.id">
          <div
            @click="toggleSelect(sub.id)"
            class="p-3 rounded-lg border cursor-pointer transition group"
            :class="selectedSubs.has(sub.id) ? 'bg-blue-950/30 border-blue-700' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="selectedSubs.has(sub.id) ? 'text-blue-400' : 'text-zinc-700'" class="text-sm">●</span>
                <span class="text-white text-sm">{{ sub.researcher_name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span v-if="subRunStatus[sub.id]" class="text-xs"
                  :class="subRunStatus[sub.id].startsWith('完成') ? 'text-green-400' : subRunStatus[sub.id] === '失败' ? 'text-red-400' : 'text-blue-400'">
                  {{ subRunStatus[sub.id] }}
                </span>
                <span v-if="runningSubs.has(sub.id)" class="inline-block w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin"></span>
                <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">{{ sub.status === 'active' ? '活跃' : '暂停' }}</span>
                <button @click.stop="deleteTopic(sub.id)" class="text-xs text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition">删除</button>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-1 mt-1.5">
              <span v-for="tag in sub.ai_keywords" :key="tag"
                class="px-1.5 py-0.5 bg-blue-900/40 text-blue-300 text-xs rounded cursor-pointer hover:bg-red-900/40 hover:text-red-300 transition"
                @click.stop="removeTag(sub, tag)" title="点击删除标签">{{ tag }} ×</span>
              <template v-if="editingTag === sub.id">
                <input v-model="newTag" @keyup.enter="addTag(sub)" @keyup.escape="doneEditing()" @blur="doneEditing()"
                  @click.stop :data-tag-input="sub.id" placeholder="标签..."
                  class="w-16 px-1 py-0.5 bg-zinc-800 border border-zinc-600 rounded text-xs text-white focus:outline-none focus:border-blue-500" />
              </template>
              <button v-else @click.stop="startEditTag(sub.id)"
                class="px-1 py-0.5 border border-dashed border-zinc-700 text-zinc-600 text-xs rounded hover:border-zinc-500 hover:text-zinc-400 transition">+ 标签</button>
            </div>
            <div class="text-xs text-zinc-600 mt-1">
              创建于 {{ new Date(sub.created_at).toLocaleDateString('zh-CN') }}
              <span v-if="getLatestBriefDate(sub.id)" class="ml-3">最新论文 {{ getLatestBriefDate(sub.id) }}</span>
            </div>
          </div>
          </template>
        </div>
      </section>

      <!-- Briefs -->
      <section v-if="briefs.length > 0">
        <h2 class="text-lg font-semibold text-zinc-300 mb-4">
          最新简报
          <span class="text-xs text-zinc-500 font-normal ml-2">↓ 从新到旧</span>
        </h2>
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

      <div v-if="topicSubs.length > 0 && briefs.length === 0" class="text-center py-10">
        <p class="text-zinc-500 text-sm mb-2">还没有简报</p>
        <p class="text-zinc-600 text-xs">选中领域 / 研究者，点击上方「立即运行」生成简报</p>
      </div>
    </template>
  </div>
</template>
