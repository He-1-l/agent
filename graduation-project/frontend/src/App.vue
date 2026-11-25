<template>
  <el-container v-if="role && $route.name !== 'login'" class="layout">
    <el-header class="header">
      <div class="brand">📚 高校自习室座位预约系统</div>
      <el-menu mode="horizontal" :default-active="$route.path" router class="menu">
        <template v-if="role === 'student'">
          <el-menu-item index="/seats">选座预约</el-menu-item>
          <el-menu-item index="/mine">我的预约</el-menu-item>
          <el-menu-item index="/profile">个人中心</el-menu-item>
        </template>
        <template v-else>
          <el-menu-item index="/admin">监控大屏</el-menu-item>
          <el-menu-item index="/admin/monitor">座位占用</el-menu-item>
          <el-menu-item index="/admin/rooms">资源与学生</el-menu-item>
          <el-menu-item index="/admin/punish">处罚管理</el-menu-item>
        </template>
      </el-menu>
      <div class="right">
        <span class="who">{{ name }}</span>
        <el-button size="small" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
  <router-view v-else />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const role = ref(localStorage.getItem('role') || '')
const name = ref(localStorage.getItem('name') || '')

// 从 localStorage 重新读取登录状态
function refreshAuth() {
  role.value = localStorage.getItem('role') || ''
  name.value = localStorage.getItem('name') || ''
}

// 登录成功后 Login 页会派发 auth-changed 事件，这里立即刷新
onMounted(() => {
  refreshAuth()
  window.addEventListener('auth-changed', refreshAuth)
})
onBeforeUnmount(() => window.removeEventListener('auth-changed', refreshAuth))

// 路由变化时也同步一次（例如刷新页面、手动改地址）
watch(() => route.fullPath, refreshAuth)

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.removeItem('name')
  role.value = ''
  router.push('/login')
}
</script>

<style>
body { margin: 0; font-family: "Microsoft YaHei", system-ui, sans-serif; background: #f5f7fa; }
.layout { min-height: 100vh; }
.header { display: flex; align-items: center; background: #1f3a5f; color: #fff; padding: 0 20px; }
.brand { font-size: 17px; font-weight: 700; margin-right: 30px; white-space: nowrap; }
.menu { flex: 1; background: transparent; border-bottom: none; }
.menu .el-menu-item { color: #cfd8e3; }
.menu .el-menu-item.is-active { color: #fff; border-bottom-color: #fff; }
.right { display: flex; align-items: center; gap: 10px; }
.who { font-size: 13px; color: #cfd8e3; }
</style>
