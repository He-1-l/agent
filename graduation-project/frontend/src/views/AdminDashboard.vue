<template>
  <div v-loading="loading">
    <el-row :gutter="16" class="cards">
      <el-col :span="6"><el-card shadow="never"><div class="kpi"><div class="num">{{ data.total_reservations }}</div><div class="cap">今日预约总数</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="kpi"><div class="num">{{ data.active_reservations }}</div><div class="cap">当前有效占用</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="kpi"><div class="num">{{ data.usage_rate }}%</div><div class="cap">整体座位使用率</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="kpi"><div class="num danger">{{ data.no_show }}</div><div class="cap">今日违约数</div></div></el-card></el-col>
    </el-row>

    <el-card shadow="never" class="main">
      <template #header>
        <div class="hd">
          <span>各自习室分时段使用率</span>
          <div>
            <el-tag :type="data.cache_enabled ? 'success' : 'warning'" size="small" style="margin-right:10px">
              {{ data.cache_enabled ? 'Redis 缓存已启用' : '降级模式（仅数据库）' }}
            </el-tag>
            <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD"
                            size="small" style="width: 140px" @change="load" />
          </div>
        </div>
      </template>
      <div ref="chartEl" style="height: 380px"></div>
    </el-card>

    <el-card shadow="never" class="main">
      <template #header>今日预约明细</template>
      <el-table :data="reservations" stripe height="300">
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="student_name" label="学生" width="100" />
        <el-table-column prop="room_name" label="自习室" min-width="140" />
        <el-table-column prop="seat_no" label="座位" width="80" />
        <el-table-column prop="slot_name" label="预约时段" width="130" />
        <el-table-column prop="created_at" label="下单时间" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="['warning','success','info','info','danger'][row.status] || 'info'">
              {{ ['待签到','已签到','已完成','已取消','违约'][row.status] || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const date = ref(new Date().toISOString().slice(0, 10))
const data = ref({ total_reservations: 0, active_reservations: 0, usage_rate: 0, no_show: 0, rows: [] })
const reservations = ref([])
const loading = ref(false)
const chartEl = ref(null)
let chart = null

async function load() {
  loading.value = true
  try {
    data.value = await api.overview(date.value)
    reservations.value = await api.adminReservations(date.value)
    await nextTick()
    render()
  } finally {
    loading.value = false
  }
}

function render() {
  if (!chartEl.value) return
  chart = chart || echarts.init(chartEl.value)
  const rooms = [...new Set(data.value.rows.map(r => r.room_name))]
  const slots = [...new Set(data.value.rows.map(r => r.slot_name))]
  const series = rooms.map(roomName => ({
    name: roomName,
    type: 'bar',
    barMaxWidth: 22,
    data: slots.map(slot => {
      const row = data.value.rows.find(r => r.room_name === roomName && r.slot_name === slot)
      return row ? row.usage_rate : 0
    })
  }))
  chart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${v}%` },
    legend: { top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: slots },
    yAxis: { type: 'value', name: '使用率(%)', max: 100 },
    series
  }, true)
}

onMounted(load)
</script>

<style scoped>
.cards { margin-bottom: 16px; }
.kpi { text-align: center; padding: 6px 0; }
.kpi .num { font-size: 26px; font-weight: 700; color: #1f3a5f; }
.kpi .num.danger { color: #f56c6c; }
.kpi .cap { font-size: 12px; color: #888; margin-top: 4px; }
.main { margin-bottom: 16px; }
.hd { display: flex; justify-content: space-between; align-items: center; }
</style>
