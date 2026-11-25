<template>
  <el-card shadow="never" v-loading="loading">
    <template #header>
      <div class="hd">
        <span>我的预约记录</span>
        <el-button size="small" @click="load">刷新</el-button>
      </div>
    </template>

    <el-table :data="rows" stripe style="width: 100%">
      <el-table-column prop="reserve_date" label="日期" width="120" />
      <el-table-column prop="slot_name" label="时段" width="130" />
      <el-table-column prop="room_name" label="自习室" min-width="160" />
      <el-table-column prop="seat_no" label="座位" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button v-if="row.status === 0" size="small" type="primary" @click="checkin(row)">签到</el-button>
          <el-button v-if="row.status === 0 || row.status === 1" size="small" @click="cancel(row)">取消</el-button>
          <el-button v-if="row.status === 1" size="small" type="success" @click="checkout(row)">签退</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!rows.length" description="还没有预约记录，去「选座预约」看看吧" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const rows = ref([])
const loading = ref(false)

const STATUS = { 0: '待签到', 1: '已签到', 2: '已完成', 3: '已取消', 4: '违约' }
const statusText = (s) => STATUS[s] ?? '未知'
const tagType = (s) => ({ 0: 'warning', 1: 'success', 2: 'info', 3: 'info', 4: 'danger' }[s] || 'info')

async function load() {
  loading.value = true
  try { rows.value = await api.myReservations() } finally { loading.value = false }
}

async function checkin(row) {
  await api.checkin(row.id)
  ElMessage.success('签到成功')
  load()
}

async function checkout(row) {
  await api.checkout(row.id)
  ElMessage.success('已签退，学习时长已记录')
  load()
}

async function cancel(row) {
  try {
    await ElMessageBox.confirm('取消后该座位将释放给其他同学，确认取消？', '提示', { type: 'warning' })
  } catch { return }
  await api.cancel(row.id)
  ElMessage.success('已取消')
  load()
}

onMounted(load)
</script>

<style scoped>
.hd { display: flex; justify-content: space-between; align-items: center; }
</style>
