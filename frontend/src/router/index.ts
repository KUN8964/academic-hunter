import { createRouter, createWebHistory } from 'vue-router'
import { auth, fetchUser, getGuestConfig } from '../stores/auth'

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
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/RegisterView.vue'),
    },
    // ── App routes (available to all, persistent features require login) ──
    {
      path: '/onboarding',
      name: 'Onboarding',
      component: () => import('../views/OnboardingView.vue'),
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/subscriptions',
      name: 'Subscriptions',
      component: () => import('../views/SubscriptionsView.vue'),
    },
    {
      path: '/briefs/:id',
      name: 'BriefDetail',
      component: () => import('../views/BriefDetailView.vue'),
    },
    {
      path: '/papers/:id',
      name: 'PaperDetail',
      component: () => import('../views/PaperDetailView.vue'),
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('../views/SearchView.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/SettingsView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  // Auto-fetch user if we have a stored token
  if (!auth.user && auth.token) {
    await fetchUser()
  }
  // No forced redirects — guest mode is always allowed
})

export default router
