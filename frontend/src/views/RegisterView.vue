<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../stores/auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await register(email.value, password.value, displayName.value || undefined)
    router.push('/onboarding')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex items-center justify-center min-h-[80vh]">
    <div class="w-full max-w-md px-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-white mb-2">创建账户</h1>
        <p class="text-zinc-500">开始追踪你的研究领域</p>
      </div>

      <form @submit.prevent="handleRegister" class="space-y-4">
        <div>
          <label class="block text-sm text-zinc-400 mb-1">显示名（选填）</label>
          <input v-model="displayName" type="text"
            class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>
        <div>
          <label class="block text-sm text-zinc-400 mb-1">邮箱</label>
          <input v-model="email" type="email" required
            class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>
        <div>
          <label class="block text-sm text-zinc-400 mb-1">密码</label>
          <input v-model="password" type="password" required minlength="6"
            class="w-full px-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition" />
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="text-center mt-6 text-sm text-zinc-500">
        已有账户？
        <router-link to="/login" class="text-blue-400 hover:underline">登录</router-link>
      </p>
    </div>
  </div>
</template>
