import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (
            id.includes('/react/') ||
            id.includes('/react-dom/') ||
            id.includes('/react-router-dom/') ||
            id.includes('/zustand/') ||
            id.includes('/axios/')
          ) {
            return 'framework'
          }

          if (id.includes('/react-markdown/') || id.includes('/remark-gfm/')) {
            return 'markdown'
          }

          if (id.includes('/mermaid/') || id.includes('/mermaid/dist/')) {
            return 'mermaid'
          }

          if (
            id.includes('/katex/')
          ) {
            return 'katex'
          }

          if (
            id.includes('/d3-') ||
            id.includes('/dagre') ||
            id.includes('/cytoscape') ||
            id.includes('/internmap/')
          ) {
            return 'graph-vendor'
          }

          return undefined
        },
      },
    },
  },
})
