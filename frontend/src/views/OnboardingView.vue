<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()

// Wizard steps: 1 = research area, 2 = researchers, 3 = confirm
const step = ref(1)
const queryText = ref('')
const researcherNames = ref('')
const loading = ref(false)
const error = ref('')

// AI suggestions
const aiKeywords = ref<string[]>([])
const suggestedSubfields = ref<string[]>([])
const suggestedResearchers = ref<any[]>([])

async function expandTopic() {
  if (!queryText.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/subscriptions/onboarding/expand', {
      query_text: queryText.value.trim(),
    })
    aiKeywords.value = data.ai_keywords || []
    suggestedSubfields.value = data.suggested_subfields || []
    suggestedResearchers.value = data.suggested_researchers || []
    step.value = 2
  } catch (e: any) {
    error.value = 'AI 扩展失败，请检查 DeepSeek API Key 配置'
  } finally {
    loading.value = false
  }
}

async function confirmAndCreate() {
  loading.value = true
  error.value = ''
  try {
    // Create topic subscription
    await api.post('/subscriptions/topics', {
      query_text: queryText.value.trim(),
    })

    // Create researcher subscriptions
    const names = researcherNames.value
      .split(/[,，、\s]+/)
      .map((n) => n.trim())
      .filter(Boolean)
    for (const name of names) {
      await api.post('/subscriptions/researchers', {
        researcher_name: name,
      })
    }

    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '创建失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-6 py-16">
    <!-- Step 1: Research Area -->
    <div v-if="step === 1">
      <h1 class="text-2xl font-bold text-white mb-2">设置你的研究关注</h1>
      <p class="text-zinc-500 mb-8">用自然语言描述你感兴趣的研究方向</p>

      <div class="space-y-4">
        <textarea v-model="queryText" rows="3"
          placeholder="例如：大模型推理优化，特别是量化和投机解码方向..."
          class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition resize-none"></textarea>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button @click="expandTopic" :disabled="loading || !queryText.trim()"
          class="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
          {{ loading ? 'AI 分析中...' : '下一步 →' }}
        </button>
      </div>
    </div>

    <!-- Step 2: Researchers -->
    <div v-if="step === 2">
      <h1 class="text-2xl font-bold text-white mb-2">追踪研究者</h1>
      <p class="text-zinc-500 mb-4">添加你想要追踪的学者（可选）</p>

      <!-- AI expanded keywords -->
      <div v-if="aiKeywords.length > 0" class="mb-6 p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
        <p class="text-sm text-zinc-400 mb-2">AI 识别的关键词：</p>
        <div class="flex flex-wrap gap-2">
          <span v-for="kw in aiKeywords" :key="kw"
            class="px-2 py-1 bg-zinc-800 text-zinc-300 text-xs rounded">{{ kw }}</span>
        </div>
      </div>

      <div class="space-y-4">
        <textarea v-model="researcherNames" rows="2"
          placeholder="输入研究者姓名，用逗号分隔，例如：Tim Dettmers, Song Han"
          class="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition resize-none"></textarea>

        <!-- Suggested researchers -->
        <div v-if="suggestedResearchers.length > 0" class="p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
          <p class="text-sm text-zinc-400 mb-2">AI 建议关注的研究者：</p>
          <div class="flex flex-wrap gap-2">
            <button v-for="r in suggestedResearchers" :key="r.name"
              @click="researcherNames += (researcherNames ? ', ' : '') + r.name"
              class="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded transition">
              + {{ r.name }}
            </button>
          </div>
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <div class="flex gap-3">
          <button @click="step = 1"
            class="flex-1 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition">
            ← 上一步
          </button>
          <button @click="confirmAndCreate" :disabled="loading"
            class="flex-1 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
            {{ loading ? '创建中...' : '确认并创建订阅' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
