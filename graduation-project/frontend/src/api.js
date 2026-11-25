import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一的后端请求入口，自动带上 JWT
const http = axios.create({
  baseURL: '/api',
  timeout: 15000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(String(msg))
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(error)
  }
)

export default {
  // 认证
  login: (data) => http.post('/auth/login', data),
  adminLogin: (data) => http.post('/auth/admin/login', data),
  register: (data) => http.post('/auth/register', data),
  me: () => http.get('/auth/me'),

  // 资源
  buildings: () => http.get('/buildings'),
  rooms: (buildingId) => http.get('/rooms', { params: { building_id: buildingId } }),
  slots: () => http.get('/slots'),
  seatMap: (roomId, date, slotId) =>
    http.get(`/rooms/${roomId}/seats`, { params: { reserve_date: date, slot_id: slotId } }),

  // 预约
  reserve: (data) => http.post('/reservations', data),
  myReservations: () => http.get('/reservations/mine'),
  cancel: (id) => http.post(`/reservations/${id}/cancel`),
  checkin: (id) => http.post(`/reservations/${id}/checkin`),
  checkout: (id) => http.post(`/reservations/${id}/checkout`),

  // 管理端
  overview: (date) => http.get('/admin/overview', { params: { stat_date: date } }),
  adminReservations: (date) => http.get('/admin/reservations', { params: { stat_date: date } }),
  students: (keyword) =>
    http.get('/admin/students', { params: keyword ? { keyword } : {} }),
  toggleStudent: (id, status) =>
    http.post(`/admin/students/${id}/status`, null, { params: { status } }),
  adminConfig: () => http.get('/admin/config'),
  // 管理端座位图：比学生端多返回「谁占的」
  adminSeatMap: (roomId, date, slotId) =>
    http.get(`/admin/rooms/${roomId}/seats`, {
      params: { reserve_date: date, slot_id: slotId }
    }),

  // 管理端：处罚与信用分
  punishments: (studentId) =>
    http.get('/admin/punishments', { params: studentId ? { student_id: studentId } : {} }),
  revokePunishment: (reservationId) =>
    http.post(`/admin/punishments/${reservationId}/revoke`),
  adjustCredit: (studentId, amount, reason) =>
    http.post(`/admin/students/${studentId}/credit`, { amount, reason }),
  creditLogs: (studentId) => http.get(`/admin/students/${studentId}/credit-logs`)
}
