<template>
  <div>
    <el-card shadow="never" class="block">
      <template #header>
        <div class="hd">
          <span>违约处罚记录</span>
          <div class="ops">
            <el-select v-model="filterStudent" clearable filterable placeholder="按学生筛选"
                       size="small" style="width: 180px" @change="loadPunishments">
              <el-option v-for="s in students" :key="s.id"
                         :label="`${s.name}（${s.student_no}）`" :value="s.id" />
            </el-select>
            <el-button size="small" @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>

      <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
        撤销处罚会把该次违约扣掉的信用分原样补回，并把记录改为「已取消」。
        撤销动作会写入信用分流水，可追溯是哪位管理员操作的。
      </el-alert>

      <el-table :data="punishments" stripe empty-text="暂无违约记录">
        <el-table-column prop="reservation_id" label="预约号" width="80" />
        <el-table-column prop="student_name" label="学生" width="100" />
        <el-table-column prop="seat_no" label="座位" width="80" />
        <el-table-column prop="room_name" label="自习室" min-width="140" />
        <el-table-column prop="reserve_date" label="日期" width="110" />
        <el-table-column prop="slot_name" label="时段" width="120" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" @click="revoke(row)">撤销处罚</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>
        <div class="hd">
          <span>学生信用分管理</span>
          <el-tag size="small" type="info">低于 {{ config.min_credit_to_reserve || 80 }} 分不能预约</el-tag>
        </div>
      </template>

      <el-table :data="students" stripe height="380">
        <el-table-column prop="student_no" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="110" />
        <el-table-column prop="class_name" label="班级" min-width="130" />
        <el-table-column label="信用分" width="110">
          <template #default="{ row }">
            <el-tag :type="creditType(row.credit_score)" size="small">{{ row.credit_score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openAdjust(row)">调整分数</el-button>
            <el-button size="small" @click="openLogs(row)">查看流水</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 调整信用分 -->
    <el-dialog v-model="adjustVisible" title="调整信用分" width="420px">
      <el-form v-if="current" label-width="90px">
        <el-form-item label="学生">
          {{ current.name }}（{{ current.student_no }}）
        </el-form-item>
        <el-form-item label="当前分数">
          <el-tag :type="creditType(current.credit_score)">{{ current.credit_score }}</el-tag>
        </el-form-item>
        <el-form-item label="变动值">
          <el-input-number v-model="adjustAmount" :min="-100" :max="100" :step="5" />
          <div class="hint">正数加分、负数扣分，范围 −100 ~ 100</div>
        </el-form-item>
        <el-form-item label="变动后">
          <b>{{ previewScore }}</b>
          <span class="hint" style="margin-left:8px">（最终限制在 0 ~ 100）</span>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="adjustReason" maxlength="100" placeholder="例如：申诉核实，恢复分数" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" :loading="adjusting" @click="submitAdjust">确定</el-button>
      </template>
    </el-dialog>

    <!-- 信用分流水 -->
    <el-dialog v-model="logsVisible" :title="`信用分流水 — ${logStudent?.name || ''}`" width="620px">
      <el-table :data="logs" stripe height="360" empty-text="暂无记录">
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="变动" width="90">
          <template #default="{ row }">
            <span :class="row.change_value > 0 ? 'up' : 'down'">
              {{ row.change_value > 0 ? '+' : '' }}{{ row.change_value }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="220" />
        <el-table-column label="关联预约" width="100">
          <template #default="{ row }">{{ row.reservation_id || '—' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const students = ref([])
const punishments = ref([])
const logs = ref([])
const config = ref({ min_credit_to_reserve: 80 })
const filterStudent = ref(null)

const adjustVisible = ref(false)
const logsVisible = ref(false)
const adjusting = ref(false)
const current = ref(null)
const logStudent = ref(null)
const adjustAmount = ref(10)
const adjustReason = ref('')

const previewScore = computed(() => {
  if (!current.value) return 0
  return Math.max(0, Math.min(100, current.value.credit_score + (adjustAmount.value || 0)))
})

function creditType(score) {
  if (score >= 90) return 'success'
  if (score >= 80) return 'warning'
  return 'danger'
}

function fmt(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 19)
}

async function loadStudents() {
  students.value = await api.students()
}

async function loadPunishments() {
  punishments.value = await api.punishments(filterStudent.value)
}

async function loadAll() {
  await Promise.all([loadStudents(), loadPunishments()])
  config.value = await api.adminConfig()
}

async function revoke(row) {
  try {
    await ElMessageBox.confirm(
      `确认撤销 ${row.student_name} 在 ${row.reserve_date} ${row.slot_name} 的违约处罚？\n` +
      '该次扣掉的信用分会被补回。',
      '撤销处罚', { type: 'warning' }
    )
  } catch { return }

  await api.revokePunishment(row.reservation_id)
  ElMessage.success('已撤销，信用分已补回')
  await loadAll()
}

function openAdjust(row) {
  current.value = row
  adjustAmount.value = 10
  adjustReason.value = ''
  adjustVisible.value = true
}

async function submitAdjust() {
  if (!adjustAmount.value) return ElMessage.warning('变动值不能为 0')
  adjusting.value = true
  try {
    const updated = await api.adjustCredit(
      current.value.id, adjustAmount.value, adjustReason.value || '管理员手动调整'
    )
    // 就地更新列表里的分数，不用整页刷新
    const target = students.value.find(s => s.id === updated.id)
    if (target) target.credit_score = updated.credit_score
    current.value = target
    ElMessage.success(`已调整为 ${updated.credit_score} 分`)
    adjustVisible.value = false
  } finally {
    adjusting.value = false
  }
}

async function openLogs(row) {
  logStudent.value = row
  logs.value = await api.creditLogs(row.id)
  logsVisible.value = true
}

onMounted(loadAll)
</script>

<style scoped>
.block { margin-bottom: 16px; }
.hd { display: flex; justify-content: space-between; align-items: center; }
.ops { display: flex; gap: 8px; }
.hint { font-size: 12px; color: #999; }
.up { color: #67c23a; font-weight: 700; }
.down { color: #f56c6c; font-weight: 700; }
</style>
