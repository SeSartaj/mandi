import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import legacy from '@vitejs/plugin-legacy'
import postcssPresetEnv from 'postcss-preset-env'
import packageJson from './package.json' with { type: 'json' }

// https://vite.dev/config/
export default defineConfig({
  server: { host: true, port: 5174, strictPort: true },
  plugins: [
    react(),
    // These ESM-capable browsers need both syntax lowering and runtime APIs.
    legacy({
      renderLegacyChunks: false,
      modernTargets: packageJson.browserslist.production,
      modernPolyfills: true,
    }),
    tailwindcss(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  css: {
    postcss: {
      plugins: [postcssPresetEnv({
        browsers: packageJson.browserslist.production,
        stage: 2,
        // Preserve native layers so Preflight cannot override CSS modules or
        // the calendar's runtime-injected styles through inflated specificity.
        features: { 'cascade-layers': false },
      })],
    },
  },
  resolve: {
    alias: {
      '@': import.meta.dirname + '/src',
    },
  },
})
