import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    cors: true, // allow any origin, TODO fix for production
    strictPort: false,
    proxy: {
      // Mirror webapp/infra/docker/nginx.conf — same top-level prefixes
      // route to the api container. dev-tail.sh runs Vite without nginx
      // in front of it, so we proxy here to keep the SPA same-origin.
      // Keep this list in sync with nginx.conf when new top-level routers
      // are mounted.
      '^/(auth|admin|agents|chat|data-store|demos|deployments|echo|health|log|mcp|providers|rest|runs|sessions|specs|users)(/|$|\\?)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Silence the wall of ECONNRESET / EPIPE / socket-hang-up
        // traces during dev. They fire when the SPA hits the proxy
        // before api is ready, when api auto-reloads, or when the
        // browser cancels a request mid-flight (common with SSE).
        // None of these are actionable; the SPA's fetch error path
        // already handles them. Replace the default stack-trace
        // logger with a single one-line note so real errors stay
        // visible.
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            const code = err.code || err.name || 'unknown';
            const noisy = ['ECONNRESET', 'EPIPE', 'ECONNREFUSED', 'ECONNABORTED'];
            if (noisy.includes(code)) {
              const url = req && req.url ? req.url : '?';
              globalThis.process.stderr.write(`[vite proxy] ${code} ${url} (transient, ignored)\n`);
            } else {
              globalThis.process.stderr.write(`[vite proxy] error: ${err.stack || err.message}\n`);
            }
            if (res && typeof res.writeHead === 'function' && !res.headersSent) {
              try {
                res.writeHead(502, { 'Content-Type': 'text/plain' });
                res.end('Bad Gateway (dev proxy: ' + code + ')');
              } catch { /* response already closed or headers sent */ }
            }
          });
        },
      },
    },
    watch: {
      ignored: [
        '**/test-results/**',
        '**/playwright-report/**',
        '**/.auth/**',
        '**/coverage/**',
        '**/htmlcov/**',
      ],
    },
  },
  
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.js',
  },
});
