import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  preview: {
    // SPA fallback for client-side routing
    headers: { "Cache-Control": "no-store" },
  },
  appType: "spa",
  server: {
    proxy: {
      "/v1": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
