import { createRouter, createWebHistory } from 'vue-router'
import { auth, fetchUser } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ── Public routes (no auth required) ──
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/SettingsView.vue'),
    },
    // ── Auth-required routes ──
    {
      path: '/onboarding',
      name: 'Onboarding',
      component: () => import('../views/OnboardingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/subscriptions',
      name: 'Subscriptions',
      component: () => import('../views/SubscriptionsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/briefs/:id',
      name: 'BriefDetail',
      component: () => import('../views/BriefDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/papers/:id',
      name: 'PaperDetail',
      component: () => import('../views/PaperDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('../views/SearchView.vue'),
    },
  ],
})

router.beforeEach(async (to, _from) => {
  // Auto-fetch user if we have a stored token
  if (!auth.user && auth.token) {
    try {
      await fetchUser()
    } catch {
      // Token is invalid — clear it
      auth.token = null
      localStorage.removeItem('token')
    }
  }

  // Redirect logged-in users away from login/register pages
  if (to.meta.guestOnly && auth.token && auth.user) {
    return '/dashboard'
  }

  // Require authentication for protected routes
  if (to.meta.requiresAuth && !auth.token) {
    return '/login'
  }
})

export default router
