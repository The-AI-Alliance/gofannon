import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    cors: true, // allow any origin, TODO fix for production
    strictPort: false,
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
