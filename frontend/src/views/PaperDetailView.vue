<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const paper = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get(`/papers/${route.params.id}`)
    paper.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-10">
    <div v-if="loading" class="text-center py-20 text-zinc-500">加载中...</div>

    <div v-else-if="paper">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-white mb-3">{{ paper.title }}</h1>
        <p class="text-zinc-400 text-sm">
          {{ paper.authors?.map((a: any) => a.name).join(', ') }}
        </p>
        <div class="flex items-center gap-3 mt-2 text-xs text-zinc-500">
          <span>{{ paper.venue || '预印本' }}</span>
          <span v-if="paper.published_at">· {{ new Date(paper.published_at).toLocaleDateString('zh-CN') }}</span>
          <span v-if="paper.source_type" class="px-1.5 py-0.5 bg-zinc-800 rounded">{{ paper.source_type }}</span>
          <span class="font-mono text-zinc-400">
            可信度 {{ paper.credibility_score?.toFixed(1) || '-' }}
          </span>
        </div>
      </div>

      <!-- AI Chinese Summary -->
      <div v-if="paper.ai_abstract_zh" class="mb-6 p-4 bg-blue-950/30 border border-blue-900/30 rounded-lg">
        <p class="text-xs text-blue-400 mb-2 font-medium">AI 中文摘要</p>
        <p class="text-zinc-300 text-sm">{{ paper.ai_abstract_zh }}</p>
      </div>

      <!-- AI Evaluation -->
      <div v-if="paper.ai_evaluation" class="mb-6 p-4 bg-amber-950/20 border border-amber-900/30 rounded-lg">
        <p class="text-xs text-amber-400 mb-2 font-medium">AI 评价</p>
        <p class="text-zinc-300 text-sm">{{ paper.ai_evaluation }}</p>
      </div>

      <!-- Original Abstract -->
      <div v-if="paper.abstract" class="mb-6">
        <p class="text-xs text-zinc-500 mb-2 font-medium">摘要原文</p>
        <p class="text-zinc-400 text-sm leading-relaxed">{{ paper.abstract }}</p>
      </div>

      <!-- Tags -->
      <div v-if="paper.ai_tags?.length" class="mb-6">
        <div class="flex flex-wrap gap-2">
          <span v-for="tag in paper.ai_tags" :key="tag"
            class="px-2 py-1 bg-zinc-800 text-zinc-400 text-xs rounded">{{ tag }}</span>
        </div>
      </div>

      <!-- Link -->
      <a v-if="paper.url" :href="paper.url" target="_blank"
        class="inline-block text-sm text-blue-400 hover:text-blue-300 transition">
        查看原文 →
      </a>
    </div>
  </div>
</template>
