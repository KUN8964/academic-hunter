<script setup lang="ts">
import { auth, logout } from './stores/auth'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-200">
    <!-- Nav -->
    <nav v-if="auth.token" class="border-b border-zinc-800 px-6 py-3 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <router-link to="/" class="text-lg font-bold text-white tracking-tight">
          🔬 Academic Hunter
        </router-link>
        <router-link to="/" class="text-sm text-zinc-400 hover:text-white transition">控制台</router-link>
        <router-link to="/subscriptions" class="text-sm text-zinc-400 hover:text-white transition">订阅</router-link>
        <router-link to="/search" class="text-sm text-zinc-400 hover:text-white transition">搜索</router-link>
      </div>
      <div class="flex items-center gap-4">
        <span v-if="auth.user" class="text-sm text-zinc-500">{{ auth.user.email }}</span>
        <button @click="logout(); router.push('/login')" class="text-sm text-zinc-500 hover:text-red-400 transition">
          退出
        </button>
      </div>
    </nav>

    <!-- Content -->
    <main>
      <router-view />
    </main>
  </div>
</template>
