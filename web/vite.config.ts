import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // `pnpm dev`: the API runs separately via `uv run python -m tracking.api`
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  build: { chunkSizeWarningLimit: 1500 }, // served from localhost only, bundle size doesn't matter
})
