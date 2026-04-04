import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 5173,
    proxy: {
      '/auth': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/papers': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/projects': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/search': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/drafts': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/analysis': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/meta': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/chat': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/references': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/notes': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/extraction': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/screening': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/clinical': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/jobs': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/billing': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/presentations': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/books': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/research': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
