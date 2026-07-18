import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import fs from 'fs'
import path from 'path'
import { defineConfig } from 'vite'

const tiptapPkgs = fs.existsSync(path.resolve(__dirname, 'node_modules/@tiptap')) 
  ? fs.readdirSync(path.resolve(__dirname, 'node_modules/@tiptap')).map(d => '@tiptap/' + d) 
  : []
const pmPkgs = fs.existsSync(path.resolve(__dirname, 'node_modules'))
  ? fs.readdirSync(path.resolve(__dirname, 'node_modules')).filter(d => d.startsWith('prosemirror-'))
  : []

export default defineConfig({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
  },
  plugins: [
    vue(),
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: `../${getAppName()}/www/aionion_crm.html`,
      },
    }),
  ],
  server: {
    allowedHosts: true,
  },
  resolve: {
    alias: {
      '@crm': path.resolve(__dirname, '../../crm/frontend/src'),
      '@framework/ui': path.resolve(__dirname, '../../frappe/ui/src'),
      '@/router': path.resolve(__dirname, 'src/router.js'),
      '@': path.resolve(__dirname, '../../crm/frontend/src'),
      '@custom': path.resolve(__dirname, 'src'),
      'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
      'vue$': path.resolve(__dirname, 'node_modules/vue'),
      'vue-router$': path.resolve(__dirname, 'node_modules/vue-router'),
      'pinia$': path.resolve(__dirname, 'node_modules/pinia'),
    },
    dedupe: [
      'vue',
      'vue-router',
      'pinia',
      'frappe-ui',
      ...tiptapPkgs,
      ...pmPkgs
    ],
  },
  optimizeDeps: {
    include: [
      'frappe-ui > feather-icons',
      'showdown',
      'tailwind.config.js',
      'engine.io-client',
      'highlight.js/lib/core',
    ],
  },
})


function getAppName() {
  // frappe-ui projects are structured as follows:
  // - apps
  //   - <app_name>
  //     - frontend
  //       - vite.config.js
  return path.basename(path.resolve(__dirname, '..'))
}
