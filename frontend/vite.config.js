import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // The site is served from https://<user>.github.io/TwinFin/, so assets and the router
  // basename both hang off this prefix.
  base: '/TwinFin/',
  server: {
    port: 5173,
    // Proxy the API so the browser only ever talks to one origin. This sidesteps CORS
    // entirely in development and means the frontend can just call `/api/chat`.
    // In production VITE_API_URL points at Render instead and this proxy is unused.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
