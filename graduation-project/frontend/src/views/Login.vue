<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="always">
      <h2>高校自习室座位预约系统</h2>
      <el-tabs v-model="tab">
        <el-tab-pane label="学生登录" name="student">
          <el-form :model="form" label-width="70px" @keyup.enter="doLogin">
            <el-form-item label="学号"><el-input v-model="form.student_no" placeholder="2022010101" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
            <el-button type="primary" style="width:100%" :loading="loading" @click="doLogin">登录</el-button>
            <div class="tip">
              演示账号：2022010101 / 123456
              <el-link type="primary" :underline="false" style="margin-left:8px" @click="tab = 'register'">
                没有账号？去注册
              </el-link>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="学生注册" name="register">
          <el-form ref="regFormRef" :model="regForm" :rules="regRules" label-width="88px">
            <el-form-item label="学号" prop="student_no">
              <el-input v-model="regForm.student_no" placeholder="例如 2023010201" maxlength="20" />
            </el-form-item>
            <el-form-item label="姓名" prop="name">
              <el-input v-model="regForm.name" placeholder="真实姓名" maxlength="50" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="regForm.password" type="password" show-password placeholder="至少 6 位" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm">
              <el-input v-model="regForm.confirm" type="password" show-password placeholder="再输一次" />
            </el-form-item>
            <el-form-item label="学院">
              <el-input v-model="regForm.college" placeholder="选填" />
            </el-form-item>
            <el-form-item label="班级">
              <el-input v-model="regForm.class_name" placeholder="选填，例如 计科2301" />
            </el-form-item>
            <el-button type="primary" style="width:100%" :loading="regLoading" @click="doRegister">
              注 册
            </el-button>
            <div class="tip">
              注册成功后自动登录，初始信用分 100
              <el-link type="primary" :underline="false" style="margin-left:8px" @click="tab = 'student'">
                已有账号？去登录
              </el-link>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="管理员登录" name="admin">
          <el-form :model="adminForm" label-width="70px" @keyup.enter="doAdminLogin">
            <el-form-item label="账号"><el-input v-model="adminForm.student_no" placeholder="admin" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="adminForm.password" type="password" show-password /></el-form-item>
            <el-button type="primary" style="width:100%" :loading="loading" @click="doAdminLogin">登录</el-button>
            <div class="tip">演示账号：admin / 123456</div>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const tab = ref('student')
const loading = ref(false)
const regLoading = ref(false)
const regFormRef = ref(null)

const form = reactive({ student_no: '', password: '' })
const adminForm = reactive({ student_no: '', password: '' })
const regForm = reactive({
  student_no: '', name: '', password: '', confirm: '',
  college: '', class_name: ''
})

// 前端先做一遍格式校验，减轻后端压力，也让提示更及时
const regRules = {
  student_no: [
    { required: true, message: '请输入学号', trigger: 'blur' },
    { min: 4, max: 20, message: '学号长度 4 到 20 位', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再输入一次密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== regForm.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur'
    }
  ]
}

function save(data) {
  localStorage.setItem('token', data.access_token)
  localStorage.setItem('role', data.role)
  localStorage.setItem('name', data.name || '')
}

async function doLogin() {
  if (!form.student_no || !form.password) return ElMessage.warning('请填写学号和密码')
  loading.value = true
  try {
    save(await api.login(form))
    ElMessage.success('登录成功')
    // 通知外层框架刷新登录状态，再跳转（不要用 location.reload，
    // 否则会在路由生效前重载，页面又回到登录页）
    window.dispatchEvent(new Event('auth-changed'))
    await router.replace('/seats')
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  const ok = await regFormRef.value.validate().catch(() => false)
  if (!ok) return

  regLoading.value = true
  try {
    const payload = {
      student_no: regForm.student_no.trim(),
      name: regForm.name.trim(),
      password: regForm.password,
      college: regForm.college || null,
      class_name: regForm.class_name || null
    }
    // 后端注册接口直接返回令牌，注册即登录
    save(await api.register(payload))
    ElMessage.success(`注册成功，欢迎你，${payload.name}`)
    window.dispatchEvent(new Event('auth-changed'))
    await router.replace('/seats')
  } finally {
    regLoading.value = false
  }
}

async function doAdminLogin() {
  if (!adminForm.student_no || !adminForm.password) return ElMessage.warning('请填写账号和密码')
  loading.value = true
  try {
    save(await api.adminLogin(adminForm))
    ElMessage.success('登录成功')
    window.dispatchEvent(new Event('auth-changed'))
    await router.replace('/admin')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #1f3a5f, #3f6ea8); }
.login-card { width: 440px; padding: 10px 14px 0; border-radius: 10px; }
h2 { text-align: center; color: #1f3a5f; margin: 10px 0 20px; font-size: 19px; }
.tip { margin-top: 12px; font-size: 12px; color: #999; text-align: center; }
/* 注册表单标签较宽，强制单行不换行，避免"确认密码"被拆成两行 */
:deep(.el-form-item__label) { white-space: nowrap; }
</style>
