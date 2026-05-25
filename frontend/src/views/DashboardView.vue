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

const router = useRouter()
const topicSubs = ref<Sub[]>([])
const researcherSubs = ref<Sub[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [t, r] = await Promise.all([
      api.get('/subscriptions/topics'),
      api.get('/subscriptions/researchers'),
    ])
    topicSubs.value = t.data
    researcherSubs.value = r.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function goOnboarding() {
  router.push('/onboarding')
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-10">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold text-white">控制台</h1>
      <button @click="goOnboarding"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition">
        + 新建订阅
      </button>
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

    <!-- Topic Subscriptions -->
    <section v-if="topicSubs.length > 0" class="mb-8">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">📚 领域订阅</h2>
      <div class="grid gap-3">
        <div v-for="sub in topicSubs" :key="sub.id"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer"
          @click="router.push(`/subscriptions`)">
          <div class="flex items-center justify-between">
            <span class="text-white font-medium">{{ sub.query_text }}</span>
            <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
              {{ sub.status === 'active' ? '活跃' : '暂停' }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Researcher Subscriptions -->
    <section v-if="researcherSubs.length > 0">
      <h2 class="text-lg font-semibold text-zinc-300 mb-4">👤 研究者追踪</h2>
      <div class="grid gap-3">
        <div v-for="sub in researcherSubs" :key="sub.id"
          class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition cursor-pointer"
          @click="router.push(`/subscriptions`)">
          <div class="flex items-center justify-between">
            <span class="text-white font-medium">{{ sub.researcher_name }}</span>
            <span :class="sub.status === 'active' ? 'text-green-400' : 'text-zinc-500'" class="text-xs">
              {{ sub.status === 'active' ? '活跃' : '暂停' }}
            </span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
