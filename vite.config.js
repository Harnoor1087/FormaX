import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy: /api/* goes to Member 2's FastAPI server, so no CORS setup is needed locally.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
});
