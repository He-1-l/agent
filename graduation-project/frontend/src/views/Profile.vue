<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <el-card shadow="never">
        <template #header>个人信息</template>
        <el-descriptions :column="1" border v-if="me">
          <el-descriptions-item label="学号">{{ me.student_no }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ me.name }}</el-descriptions-item>
          <el-descriptions-item label="学院">{{ me.college || '—' }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ me.major || '—' }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ me.class_name || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="credit">
          <div class="label">信用分</div>
          <el-progress :percentage="me?.credit_score || 0"
                       :color="creditColor" :stroke-width="16" text-inside />
          <div class="hint">低于 80 分将无法预约，违约一次扣 5 分</div>
        </div>
      </el-card>
    </el-col>

    <el-col :span="14">
      <el-card shadow="never">
        <template #header>学习时长统计（近 7 条已完成记录）</template>
        <div ref="chartEl" style="height: 320px"></div>
        <el-empty v-if="!finished.length" description="暂无已完成的学习记录" />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const me = ref(null)
const finished = ref([])
const chartEl = ref(null)
let chart = null

const creditColor = computed(() => {
  const s = me.value?.credit_score ?? 100
  if (s >= 90) return '#67c23a'
  if (s >= 80) return '#e6a23c'
  return '#f56c6c'
})

async function load() {
  me.value = await api.me()
  const all = await api.myReservations()
  finished.value = all.filter(r => r.status === 2).slice(0, 7).reverse()
  await nextTick()
  if (chartEl.value && finished.value.length) render()
}

function render() {
  chart = chart || echarts.init(chartEl.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: finished.value.map(r => `${r.reserve_date.slice(5)} ${r.slot_name.slice(0,5)}`) },
    yAxis: { type: 'value', name: '预约数' },
    series: [{
      type: 'bar', barWidth: 26, itemStyle: { color: '#3f6ea8' },
      data: finished.value.map(() => 1)
    }]
  })
}

onMounted(load)
</script>

<style scoped>
.credit { margin-top: 20px; }
.credit .label { font-size: 13px; color: #666; margin-bottom: 8px; }
.credit .hint { font-size: 12px; color: #999; margin-top: 8px; }
</style>
