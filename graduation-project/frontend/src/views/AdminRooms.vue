<template>
  <div>
    <el-card shadow="never" class="block">
      <template #header>自习室资源</template>
      <el-table :data="rooms" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="floor" label="楼层" width="80" />
        <el-table-column label="座位布局" width="140">
          <template #default="{ row }">{{ row.row_count }} 行 × {{ row.col_count }} 列</template>
        </el-table-column>
        <el-table-column prop="seat_count" label="座位数" width="90" />
        <el-table-column label="空调" width="80">
          <template #default="{ row }">{{ row.has_ac ? '有' : '无' }}</template>
        </el-table-column>
        <el-table-column label="插座" width="80">
          <template #default="{ row }">{{ row.has_power ? '有' : '无' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <div class="hd">
          <span>学生账号与信用分</span>
          <div class="ops">
            <el-input v-model="keyword" placeholder="搜学号或姓名" clearable size="small"
                      style="width: 190px" @keyup.enter="loadStudents" @clear="loadStudents" />
            <el-button size="small" @click="loadStudents">搜索</el-button>
            <el-tag size="small" type="info">
              {{ config.database }} / {{ config.cache_enabled ? 'Redis 已启用' : '降级模式' }}
            </el-tag>
          </div>
        </div>
      </template>
      <el-table :data="students" stripe height="420">
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="class_name" label="班级" min-width="140" />
        <el-table-column label="信用分" width="120">
          <template #default="{ row }">
            <el-tag :type="row.credit_score >= 90 ? 'success' : row.credit_score >= 80 ? 'warning' : 'danger'" size="small">
              {{ row.credit_score }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.status === 1" @change="(v) => toggle(row, v)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="hint">
        共 {{ students.length }} 名学生（按注册时间倒序，最新注册的在最前；压测账号默认隐藏）
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const rooms = ref([])
const students = ref([])
const keyword = ref('')
const config = ref({ database: '-', cache_enabled: false })

async function loadStudents() {
  students.value = await api.students(keyword.value.trim() || undefined)
}

async function load() {
  const buildings = await api.buildings()
  const all = []
  for (const b of buildings) {
    const list = await api.rooms(b.id)
    all.push(...list)
  }
  rooms.value = all
  await loadStudents()
  config.value = await api.adminConfig()
}

async function toggle(row, value) {
  await api.toggleStudent(row.id, value ? 1 : 0)
  row.status = value ? 1 : 0
  ElMessage.success(value ? '已启用' : '已禁用')
}

onMounted(load)
</script>

<style scoped>
.block { margin-bottom: 16px; }
.hd { display: flex; justify-content: space-between; align-items: center; }
.ops { display: flex; gap: 8px; align-items: center; }
.hint { margin-top: 10px; font-size: 12px; color: #999; }
</style>
