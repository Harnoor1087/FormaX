import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { spawn } from 'node:child_process';

function pythonBackendPlugin() {
  let proc = null;
  return {
    name: 'python-backend',
    configureServer() {
      try {
        proc = spawn('python3', ['-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8001', '--reload'], {
          stdio: 'pipe',
        });
        proc.stdout?.on('data', (d) => process.stdout.write(`[FastAPI] ${d}`));
        proc.stderr?.on('data', (d) => process.stderr.write(`[FastAPI] ${d}`));
        proc.on('error', (err) => console.error('[FastAPI spawn error]', err));
      } catch (err) {
        console.error('[FastAPI launch error]', err);
      }

      const cleanup = () => {
        if (proc) {
          try { proc.kill(); } catch {}
          proc = null;
        }
      };

      process.on('exit', cleanup);
      process.on('SIGINT', cleanup);
      process.on('SIGTERM', cleanup);
    },
  };
}

// Dev proxy: /api/* goes to Member 2's FastAPI server, so no CORS setup is needed locally.
export default defineConfig({
  plugins: [react(), pythonBackendPlugin()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: { '/api': { target: 'http://localhost:8001', changeOrigin: true } },
  },
});
