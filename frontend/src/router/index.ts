import { createRouter, createWebHistory } from 'vue-router'
import { auth, fetchUser } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/onboarding',
      name: 'Onboarding',
      component: () => import('../views/OnboardingView.vue'),
      meta: { auth: true },
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { auth: true },
    },
    {
      path: '/subscriptions',
      name: 'Subscriptions',
      component: () => import('../views/SubscriptionsView.vue'),
      meta: { auth: true },
    },
    {
      path: '/briefs/:id',
      name: 'BriefDetail',
      component: () => import('../views/BriefDetailView.vue'),
      meta: { auth: true },
    },
    {
      path: '/papers/:id',
      name: 'PaperDetail',
      component: () => import('../views/PaperDetailView.vue'),
      meta: { auth: true },
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('../views/SearchView.vue'),
      meta: { auth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  if (!auth.user && auth.token) {
    await fetchUser()
  }
  if (to.meta.auth && !auth.token) {
    return '/login'
  }
  if (to.meta.guest && auth.token) {
    return '/'
  }
})

export default router
