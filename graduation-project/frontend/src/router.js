import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/seats' },
  { path: '/login', name: 'login', component: () => import('./views/Login.vue') },
  { path: '/seats', name: 'seats', component: () => import('./views/SeatMap.vue') },
  { path: '/mine', name: 'mine', component: () => import('./views/MyReservations.vue') },
  { path: '/profile', name: 'profile', component: () => import('./views/Profile.vue') },
  { path: '/admin', name: 'admin', component: () => import('./views/AdminDashboard.vue') },
  { path: '/admin/monitor', name: 'adminMonitor', component: () => import('./views/AdminSeatMonitor.vue') },
  { path: '/admin/rooms', name: 'adminRooms', component: () => import('./views/AdminRooms.vue') },
  { path: '/admin/punish', name: 'adminPunish', component: () => import('./views/AdminPunish.vue') }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 简单的登录拦截：没令牌一律回到登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'login' && !token) return { name: 'login' }
  return true
})

export default router
