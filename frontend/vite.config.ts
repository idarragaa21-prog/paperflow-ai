import { defineConfig } from 'vitest/config'
import type { ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'

const API_TARGET = 'http://127.0.0.1:8000';
const apiPrefixes = [
  '/auth',
  '/health',
  '/papers',
  '/projects',
  '/search',
  '/drafts',
  '/analysis',
  '/meta',
  '/chat',
  '/references',
  '/notes',
  '/extraction',
  '/screening',
  '/clinical',
  '/jobs',
  '/billing',
  '/presentations',
  '/books',
  '/research',
];

function proxyWithHtmlBypass(target: string): ProxyOptions {
  return {
    target,
    changeOrigin: true,
    bypass(req) {
      const accept = req.headers?.accept || '';
      const isDocumentRequest = req.method === 'GET' && accept.includes('text/html');
      if (isDocumentRequest) {
        return req.url;
      }
      return undefined;
    },
  };
}

const proxy = Object.fromEntries(
  apiPrefixes.map((prefix) => [prefix, proxyWithHtmlBypass(API_TARGET)]),
);

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 5173,
    proxy,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
