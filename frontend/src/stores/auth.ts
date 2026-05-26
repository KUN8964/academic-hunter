import { reactive, computed } from 'vue'
import api from '../api'

interface User {
  id: string
  email: string
  display_name: string | null
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
}

export const auth = reactive<AuthState>({
  user: null,
  token: localStorage.getItem('token'),
  loading: false,
})

// Guest mode: API key stored in localStorage, no account needed
export function getGuestConfig() {
  return {
    ai_api_key: localStorage.getItem('guest_api_key') || '',
    ai_base_url: localStorage.getItem('guest_base_url') || '',
    ai_model: localStorage.getItem('guest_model') || '',
    s2_api_key: localStorage.getItem('guest_s2_key') || '',
  }
}

export function setGuestConfig(key: string, baseUrl: string, model: string) {
  localStorage.setItem('guest_api_key', key)
  if (baseUrl) localStorage.setItem('guest_base_url', baseUrl)
  else localStorage.removeItem('guest_base_url')
  if (model) localStorage.setItem('guest_model', model)
  else localStorage.removeItem('guest_model')
}

export const isGuest = computed(() => !auth.token && !!localStorage.getItem('guest_api_key'))

// ── Auth actions ──

export async function login(email: string, password: string) {
  const { data } = await api.post('/auth/login', { email, password })
  auth.token = data.access_token
  localStorage.setItem('token', data.access_token)
  await fetchUser()
  // Merge guest settings if they exist (guest used before login)
  await migrateGuestSettings()
}

export async function register(email: string, password: string, display_name?: string) {
  const { data } = await api.post('/auth/register', { email, password, display_name })
  auth.token = data.access_token
  localStorage.setItem('token', data.access_token)
  await fetchUser()
  // Migrate guest API settings to the new account
  await migrateGuestSettings()
}

export async function fetchUser() {
  if (!auth.token) return
  try {
    const { data } = await api.get('/auth/me')
    auth.user = data
  } catch {
    auth.token = null
    localStorage.removeItem('token')
  }
}

export function logout() {
  auth.token = null
  auth.user = null
  localStorage.removeItem('token')
}

// ── Guest → Account migration ──

async function migrateGuestSettings() {
  const guestKey = localStorage.getItem('guest_api_key')
  const guestBase = localStorage.getItem('guest_base_url')
  const guestModel = localStorage.getItem('guest_model')
  const guestS2 = localStorage.getItem('guest_s2_key')

  if (!guestKey && !guestBase && !guestModel && !guestS2) return

  try {
    const payload: Record<string, string | null> = {}
    if (guestKey) payload.ai_api_key = guestKey
    if (guestBase) payload.ai_base_url = guestBase
    else payload.ai_base_url = null
    if (guestModel) payload.ai_model = guestModel
    else payload.ai_model = null
    if (guestS2) payload.s2_api_key = guestS2
    else payload.s2_api_key = null

    await api.put('/auth/settings', payload)

    // Clear guest localStorage after successful migration
    localStorage.removeItem('guest_api_key')
    localStorage.removeItem('guest_base_url')
    localStorage.removeItem('guest_model')
    localStorage.removeItem('guest_s2_key')
  } catch {
    // Silent — migration is best-effort
  }
}
