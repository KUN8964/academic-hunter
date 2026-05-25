import { reactive } from 'vue'
import api from './api'

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

export async function login(email: string, password: string) {
  const { data } = await api.post('/auth/login', { email, password })
  auth.token = data.access_token
  localStorage.setItem('token', data.access_token)
  await fetchUser()
}

export async function register(email: string, password: string, display_name?: string) {
  const { data } = await api.post('/auth/register', { email, password, display_name })
  auth.token = data.access_token
  localStorage.setItem('token', data.access_token)
  await fetchUser()
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
