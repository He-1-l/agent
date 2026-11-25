<template>
  <div>
    <el-card shadow="never" class="toolbar">
      <el-form inline>
        <el-form-item label="场馆">
          <el-select v-model="buildingId" style="width: 150px" @change="loadRooms">
            <el-option v-for="b in buildings" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="自习室">
          <el-select v-model="roomId" style="width: 200px" @change="reload">
            <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD"
                          :disabled-date="disableDate" style="width: 150px" @change="onDateChange" />
        </el-form-item>
        <el-form-item label="时段">
          <el-select v-model="slotId" style="width: 190px" @change="reload">
            <el-option v-for="s in availableSlots" :key="s.id"
                       :label="`${s.start_time.slice(0,5)}-${s.end_time.slice(0,5)}${isOngoing(s) ? '（进行中）' : ''}`"
                       :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-tag v-if="!availableSlots.length" type="warning" size="small">
            今天已无剩余时段，请选择明天
          </el-tag>
          <el-tag v-else-if="currentSlotOngoing" type="warning" size="small">
            时段进行中 · 可捡漏已释放的座位
          </el-tag>
          <el-tag v-else :type="wsConnected ? 'success' : 'info'" size="small">
            {{ wsConnected ? '实时已连接' : '实时未连接' }}
          </el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" v-loading="loading">
      <div class="legend">
        <span><i class="dot free"></i>空闲</span>
        <span><i class="dot reserved"></i>已预约</span>
        <span><i class="dot mine"></i>我占的</span>
        <span><i class="dot maintenance"></i>维修中</span>
        <span><span class="bolt-demo">⚡</span> 有电源插座</span>
      </div>

      <div class="seat-grid" :style="{ gridTemplateColumns: `repeat(${room?.col_count || 8}, 1fr)` }">
        <div v-for="seat in seats" :key="seat.id"
             class="seat" :class="seatClass(seat)"
             :title="seatTitle(seat)"
             @click="pick(seat)">
          {{ seat.seat_no }}
          <span v-if="seat.has_power" class="bolt">⚡</span>
        </div>
      </div>

      <el-empty v-if="!seats.length" description="该时段暂无座位数据" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const buildings = ref([])
const rooms = ref([])
const slots = ref([])
const seats = ref([])
const room = ref(null)
const buildingId = ref(null)
const roomId = ref(null)
const slotId = ref(1)
const date = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const wsConnected = ref(false)
const mySeats = ref(new Set())

let socket = null

function disableDate(d) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const max = new Date(today); max.setDate(max.getDate() + 1)
  return d < today || d > max
}

function todayStr() {
  const t = new Date()
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`
}

// 可预约的时段规则（与后端保持一致）：
//   · 时段还没开始 —— 可以约
//   · 时段进行中，但距结束还够 MIN_REMAINING 分钟 —— 也可以约（捡漏被释放的座位）
//   · 时段已结束，或剩得太少 —— 不可约
// 这样「超时未签到释放座位」才有意义：释放出来的座位能被后来的人接走。
const MIN_REMAINING_MINUTES = 30

const availableSlots = computed(() => {
  if (date.value !== todayStr()) return slots.value   // 明天全天可约
  const now = new Date()
  const curSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
  return slots.value.filter((s) => {
    const [eh, em] = s.end_time.split(':').map(Number)
    const endSec = eh * 3600 + em * 60
    // 距结束不足 30 分钟就排除（含已结束的）
    return endSec - curSec >= MIN_REMAINING_MINUTES * 60
  })
})

// 判断某个时段是否「正在进行中」，用于在界面上加提示
function isOngoing(slot) {
  if (date.value !== todayStr()) return false
  const now = new Date()
  const curSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
  const [sh, sm] = slot.start_time.split(':').map(Number)
  return curSec >= sh * 3600 + sm * 60
}

function onDateChange() {
  if (availableSlots.value.length &&
      !availableSlots.value.some((s) => s.id === slotId.value)) {
    slotId.value = availableSlots.value[0].id
  }
  reload()
}

function seatClass(seat) {
  if (seat.state === 'maintenance') return 'is-maintenance'
  if (mySeats.value.has(seat.id)) return 'is-mine'
  return seat.state === 'reserved' ? 'is-reserved' : 'is-free'
}

// 当前选中的时段是否正在进行中（用于顶部提示与确认框文案）
const currentSlotOngoing = computed(() => {
  const slot = slots.value.find((s) => s.id === slotId.value)
  return slot ? isOngoing(slot) : false
})

// 鼠标悬停时的提示文字
function seatTitle(seat) {
  const power = seat.has_power ? '· 有电源插座' : ''
  if (seat.state === 'maintenance') return '维修中，暂不可用'
  if (mySeats.value.has(seat.id)) return `${seat.seat_no} · 我预约的座位 ${power}`
  if (seat.state === 'reserved') return `${seat.seat_no} · 已被他人预约 ${power}`
  return `${seat.seat_no} · 空闲，点击预约 ${power}`
}

async function loadRooms() {
  rooms.value = await api.rooms(buildingId.value)
  if (rooms.value.length) { roomId.value = rooms.value[0].id; await reload() }
}

async function reload() {
  if (!roomId.value) return
  loading.value = true
  try {
    const data = await api.seatMap(roomId.value, date.value, slotId.value)
    room.value = data.room
    seats.value = data.seats
    // 只把「当前日期 + 当前时段」下属于我的预约标成"我占的"。
    // 之前没按日期和时段过滤，导致切到别的时段时这个座位还是黄的。
    const mine = await api.myReservations()
    const set = new Set()
    mine.filter((r) => (r.status === 0 || r.status === 1)
        && r.reserve_date === date.value
        && String(r.slot_id) === String(slotId.value))
        .forEach((r) => set.add(r.seat_id))
    mySeats.value = set
    connectWs()
  } finally {
    loading.value = false
  }
}

function connectWs() {
  if (socket) { socket.close(); socket = null }
  if (!roomId.value) return
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  socket = new WebSocket(`${proto}://${location.host}/ws/rooms/${roomId.value}`)
  socket.onopen = () => { wsConnected.value = true }
  socket.onclose = () => { wsConnected.value = false }
  socket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (!msg.seat_id) return
      const seat = seats.value.find(s => s.id === msg.seat_id)
      if (!seat) return
      // 只重绘这一个座位，不整页刷新
      seat.state = msg.event === 'released' ? 'free' : 'reserved'
    } catch { /* 忽略心跳 */ }
  }
}

async function pick(seat) {
  if (seat.state === 'maintenance') return ElMessage.warning('该座位维修中')
  if (seat.state === 'reserved' && !mySeats.value.has(seat.id)) {
    return ElMessage.warning('该座位已被预约')
  }
  // 进行中的时段是"捡漏"，提示语要说清楚签到时限是从现在算起
  const ongoing = currentSlotOngoing.value
  const tip = ongoing
    ? `确认预约 ${room.value?.name || ''} ${seat.seat_no} 座位？\n` +
      '该时段正在进行中，签到截止时间将从现在重新计算（15 分钟内）。'
    : `确认预约 ${room.value?.name || ''} ${seat.seat_no} 座位？`
  try {
    await ElMessageBox.confirm(tip, '预约确认', { type: 'info' })
  } catch { return }

  try {
    await api.reserve({ seat_id: seat.id, reserve_date: date.value, slot_id: slotId.value })
    ElMessage.success('预约成功，请记得按时签到')
    await reload()
  } catch { /* 错误提示已在拦截器里弹出 */ }
}

onMounted(async () => {
  buildings.value = await api.buildings()
  slots.value = await api.slots()
  // 默认选中今天第一个还没开始的时段
  if (availableSlots.value.length) slotId.value = availableSlots.value[0].id
  if (buildings.value.length) { buildingId.value = buildings.value[0].id; await loadRooms() }
})

onBeforeUnmount(() => { if (socket) socket.close() })

const roomName = computed(() => room.value?.name || '')
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
.legend { display: flex; gap: 18px; font-size: 13px; color: #666; margin-bottom: 14px; flex-wrap: wrap; }
.bolt-demo { font-size: 11px; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.dot.free { background: #c8e6c9; border: 1px solid #81c784; }
.dot.reserved { background: #ffcdd2; border: 1px solid #e57373; }
.dot.mine { background: #ffe082; border: 1px solid #ffb300; }
.dot.maintenance { background: #e0e0e0; border: 1px solid #bdbdbd; }
.seat-grid { display: grid; gap: 10px; max-width: 760px; }
.seat {
  position: relative; height: 54px; display: flex; align-items: center; justify-content: center;
  font-size: 12px; border-radius: 6px; cursor: pointer; user-select: none; transition: transform .12s;
  border: 1px solid transparent;
}
.seat:hover { transform: translateY(-2px); }
.is-free { background: #c8e6c9; border-color: #81c784; color: #256029; }
.is-reserved { background: #ffcdd2; border-color: #e57373; color: #a33; cursor: not-allowed; }
.is-mine { background: #ffe082; border-color: #ffb300; color: #7a5b00; }
.is-maintenance { background: #e0e0e0; border-color: #bdbdbd; color: #888; cursor: not-allowed; }
.bolt { position: absolute; top: 2px; right: 3px; font-size: 9px; }
</style>
