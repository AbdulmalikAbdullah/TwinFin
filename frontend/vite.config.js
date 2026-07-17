import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// export default defineConfig({
//   plugins: [react()],
//   server: {
//     port: 5173,
//     // Proxy the API so the browser only ever talks to one origin. This sidesteps CORS
//     // entirely in development and means the frontend can just call `/api/chat`.
//     proxy: {
//       '/api': {
//         target: 'http://127.0.0.1:5000',
//         changeOrigin: true,
//       },
//     },
//   },
// })

export default defineConfig({
  plugins: [react()],
  base: '/TwinFin/'
})