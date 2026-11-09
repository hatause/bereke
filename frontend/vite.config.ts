import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

const proxy = { '/api': 'http://127.0.0.1:8000' }
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true, proxy,
    fs: { strict: true, allow: [fileURLToPath(new URL('.', import.meta.url))], deny: ['**/.env*', '**/sources/**', '**/data/**', '**/.local/**', '**/*.{pdf,pptx,xlsx}'] },
  },
  preview: { proxy },
  build: { sourcemap: false },
  test: { include: ['src/**/*.test.ts'] },
})
