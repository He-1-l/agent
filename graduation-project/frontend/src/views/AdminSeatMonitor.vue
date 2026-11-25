<template>
  <div>
    <el-card shadow="never" class="block">
      <el-form inline>
        <el-form-item label="自习室">
          <el-select v-model="roomId" style="width: 200px" @change="loadAndResubscribe">
            <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD"
                          style="width: 150px" @change="loadAndResubscribe" />
        </el-form-item>
        <el-form-item label="时段">
          <el-select v-model="slotId" style="width: 170px" @change="loadAndResubscribe">
            <el-option v-for="s in slots" :key="s.id"
                       :label="`${s.start_time.slice(0,5)}-${s.end_time.slice(0,5)}`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-tag size="small" :type="wsConnected ? 'success' : 'info'">
            {{ wsConnected ? '实时已连接' : '实时未连接' }}
          </el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="never" v-loading="loading">
          <template #header>
            <div class="hd">
              <span>{{ roomName }} · {{ slotName }} · 座位占用</span>
              <span class="summary">
                共 {{ seats.length }} 座，
                <b class="free-c">{{ freeCount }}</b> 空闲，
                <b class="used-c">{{ usedCount }}</b> 已占
              </span>
            </div>
          </template>

          <div class="legend">
            <span><i class="dot free"></i>空闲</span>
            <span><i class="dot taken"></i>已预约</span>
            <span><i class="dot checked"></i>已签到</span>
            <span><i class="dot broken"></i>维修中</span>
            <span class="tip-text">点击座位查看占用者信息</span>
          </div>

          <div class="seat-grid" :style="{ gridTemplateColumns: `repeat(${room?.col_count || 8}, 1fr)` }">
            <div v-for="seat in seats" :key="seat.id"
                 class="seat" :class="seatClass(seat)"
                 :title="seatTitle(seat)"
                 @click="showDetail(seat)">
              <span class="no">{{ seat.seat_no }}</span>
              <span v-if="seat.student_name" class="who">{{ shortName(seat.student_name) }}</span>
              <span v-if="seat.has_power" class="bolt">⚡</span>
            </div>
          </div>
          <el-empty v-if="!seats.length" description="暂无座位数据" />
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>占用详情</template>
          <el-descriptions v-if="selected" :column="1" border size="small">
            <el-descriptions-item label="座位">{{ selected.seat_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small" :type="tagType(selected)">{{ stateText(selected) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="占用者">
              {{ selected.student_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="学号">
              {{ selected.student_no || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="预约号">
              {{ selected.reservation_id || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="签到截止">
              {{ fmt(selected.checkin_deadline) }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="点击左侧座位查看详情" :image-size="70" />

          <div v-if="selected && selected.student_name" class="ops">
            <el-button size="small" type="danger" plain @click="release(selected)">
              强制释放该座位
            </el-button>
          </div>
        </el-card>

        <el-card shadow="never" style="margin-top:16px">
          <template #header>当前时段占用清单</template>
          <el-table :data="occupied" size="small" height="300" empty-text="该时段无人占用">
            <el-table-column prop="seat_no" label="座位" width="70" />
            <el-table-column prop="student_name" label="占用者" width="90" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="tagType(row)">{{ stateText(row) }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const rooms = ref([])
const slots = ref([])
const seats = ref([])
const room = ref(null)
const roomId = ref(null)
const slotId = ref(1)
const date = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const selected = ref(null)
const wsConnected = ref(false)
let socket = null
let subscribedRoomId = null   // 当前已订阅的房间，避免重复建连

const roomName = computed(() => room.value?.name || '')
const slotName = computed(() => {
  const s = slots.value.find((x) => x.id === slotId.value)
  return s ? `${s.start_time.slice(0, 5)}-${s.end_time.slice(0, 5)}` : ''
})
const freeCount = computed(() => seats.value.filter((s) => s.state === 'free').length)
const usedCount = computed(() => seats.value.filter((s) => s.state === 'reserved').length)
const occupied = computed(() => seats.value.filter((s) => s.student_name))

function shortName(n) {
  if (!n) return ''
  return n.length > 2 ? n.slice(0, 2) : n
}

function seatClass(seat) {
  if (seat.state === 'maintenance') return 'is-broken'
  if (seat.state !== 'reserved') return 'is-free'
  return seat.res_status === 1 ? 'is-checked' : 'is-taken'
}

function stateText(seat) {
  if (seat.state === 'maintenance') return '维修中'
  if (seat.state === 'free') return '空闲'
  return seat.res_status === 1 ? '已签到' : '待签到'
}

function tagType(seat) {
  if (seat.state === 'maintenance') return 'info'
  if (seat.state === 'free') return 'success'
  return seat.res_status === 1 ? 'primary' : 'warning'
}

function seatTitle(seat) {
  if (seat.state === 'maintenance') return `${seat.seat_no} · 维修中`
  if (seat.state === 'free') return `${seat.seat_no} · 空闲`
  return `${seat.seat_no} · ${seat.student_name}（${seat.student_no}）${stateText(seat)}`
}

function fmt(t) {
  if (!t) return '—'
  return String(t).replace('T', ' ').slice(0, 16)
}

function showDetail(seat) {
  selected.value = seat
}

async function load() {
  if (!roomId.value) return
  loading.value = true
  try {
    const data = await api.adminSeatMap(roomId.value, date.value, slotId.value)
    room.value = data.room
    seats.value = data.seats
    // 注意：这里不要重置 selected，否则用户点开的详情面板会被刷掉
  } finally {
    loading.value = false
  }
}

// 切换房间/日期/时段时：先刷新数据，再重新订阅
async function loadAndResubscribe() {
  await load()
  connectWs()
}

function connectWs() {
  // 已经连到同一个房间就不重复建连，避免每次刷新都重连
  if (socket && socket.readyState === WebSocket.OPEN && subscribedRoomId === roomId.value) {
    return
  }
  if (socket) {
    try { socket.close() } catch (e) { /* 忽略 */ }
    socket = null
  }
  if (!roomId.value) return

  subscribedRoomId = roomId.value
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws/rooms/${roomId.value}`)
  socket = ws

  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    if (socket === ws) socket = null
  }
  ws.onerror = () => { wsConnected.value = false }

  ws.onmessage = (ev) => {
    // 心跳回包与连接欢迎消息都不触发刷新，否则会形成
    // 「收到消息 → 刷新 → 重连 → 又收到欢迎消息」的无限循环
    let msg = null
    try { msg = JSON.parse(ev.data) } catch (e) { return }
    if (!msg || msg.event === 'connected') return
    if (!msg.seat_id) return

    // 只更新这一个座位，并同步该座位的占用者信息
    refreshSeat(msg.seat_id, msg.event)
  }
}

// 单座位增量更新：不再整页重拉，避免闪烁
async function refreshSeat(seatId, event) {
  const seat = seats.value.find((s) => s.id === seatId)
  if (!seat) return

  if (event === 'released') {
    seat.state = 'free'
    seat.student_name = null
    seat.student_no = null
    seat.reservation_id = null
    seat.checkin_deadline = null
    seat.res_status = null
  } else {
    // 被预约/签到：重拉一次拿到占用者信息，但只影响这一个座位
    seat.state = 'reserved'
    try {
      const data = await api.adminSeatMap(roomId.value, date.value, slotId.value)
      const fresh = data.seats.find((s) => s.id === seatId)
      if (fresh) Object.assign(seat, fresh)
    } catch (e) { /* 忽略，保持原状态 */ }
  }
  // 详情面板正显示这个座位时同步更新
  if (selected.value && selected.value.id === seatId) {
    selected.value = seat
  }
}

async function release(seat) {
  try {
    await ElMessageBox.confirm(
      `确认强制释放 ${seat.seat_no}（占用者 ${seat.student_name}）？\n` +
      '释放后该座位立即可被其他同学预约。',
      '强制释放', { type: 'warning' }
    )
  } catch { return }
  // 复用学生端的取消接口不适用（管理员不是预约人），这里提示改用撤销处罚或让学生自行取消
  ElMessage.warning('强制释放需要学生本人取消，或在「处罚管理」中撤销对应记录')
}

onMounted(async () => {
  const buildings = await api.buildings()
  const all = []
  for (const b of buildings) {
    const list = await api.rooms(b.id)
    all.push(...list)
  }
  rooms.value = all
  slots.value = await api.slots()
  if (all.length) {
    roomId.value = all[0].id
    await loadAndResubscribe()   // 首次加载：拉数据 + 建立订阅
  }
})

onBeforeUnmount(() => {
  if (socket) {
    try { socket.close() } catch (e) { /* 忽略 */ }
    socket = null
  }
  subscribedRoomId = null
})

onBeforeUnmount(() => {
  if (socket) {
    try { socket.close() } catch (e) { /* 忽略 */ }
    socket = null
  }
  subscribedRoomId = null
})
</script>

<style scoped>
.block { margin-bottom: 16px; }
.hd { display: flex; justify-content: space-between; align-items: center; }
.summary { font-size: 13px; color: #888; }
.free-c { color: #67c23a; }
.used-c { color: #e6a23c; }
.legend { display: flex; gap: 16px; font-size: 13px; color: #666; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.dot.free { background: #c8e6c9; border: 1px solid #81c784; }
.dot.taken { background: #ffe0b2; border: 1px solid #ffb74d; }
.dot.checked { background: #bbdefb; border: 1px solid #64b5f6; }
.dot.broken { background: #e0e0e0; border: 1px solid #bdbdbd; }
.tip-text { color: #aaa; font-size: 12px; }
.seat-grid { display: grid; gap: 8px; }
.seat {
  position: relative; height: 58px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; font-size: 11px;
  border-radius: 6px; cursor: pointer; user-select: none;
  transition: transform .1s, box-shadow .1s; border: 1px solid transparent;
}
.seat:hover { transform: translateY(-2px); box-shadow: 0 3px 8px rgba(0,0,0,.12); }
.is-free { background: #c8e6c9; border-color: #81c784; color: #256029; }
.is-taken { background: #ffe0b2; border-color: #ffb74d; color: #8a5a00; }
.is-checked { background: #bbdefb; border-color: #64b5f6; color: #0d47a1; }
.is-broken { background: #e0e0e0; border-color: #bdbdbd; color: #888; cursor: not-allowed; }
.no { font-weight: 600; }
.who { font-size: 10px; opacity: .85; margin-top: 1px; }
.bolt { position: absolute; top: 2px; right: 3px; font-size: 9px; }
.ops { margin-top: 12px; }
</style>
