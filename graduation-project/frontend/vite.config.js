import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // Windows 下用"临时文件 + 重命名"方式保存时，Vite 的文件监听器会去监听
    // 那个瞬时存在的临时目录并抛出 EBUSY 导致整个开发服务器崩溃。
    // 这里忽略临时文件，并改用轮询方式监听，稳定性优先。
    watch: {
      usePolling: true,
      interval: 300,
      ignored: ['**/.*.tmpdir/**', '**/*.tmp', '**/node_modules/**', '**/.git/**']
    },
    proxy: {
      // 前端开发服务器把 /api 与 /ws 转发到后端，避免跨域
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true }
    }
  }
})
