import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.config.*',
        '**/*.spec.*',
        '**/*.test.*',
        '**/dist/',
        '**/build/',
        'src/main.jsx',
        'src/App.jsx',
        'src/pages/**/*',
        'src/contexts/**/*',
        'src/extensions/**/*',
        'src/theme.js',
        'src/config.js',
      ],
      thresholds: {
        lines: 20,
        functions: 45,
        branches: 70,
        statements: 20,
      },
    },
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],
    exclude: ['node_modules', 'dist', 'build', '.idea', '.git', '.cache'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
