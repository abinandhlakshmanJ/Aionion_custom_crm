import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import frappeui from '../../crm/frontend/node_modules/frappe-ui/vite/index.js'
import fs from 'fs'
import path from 'path'
import { defineConfig } from 'vite'

const crmNodeModules = path.resolve(__dirname, '../../crm/frontend/node_modules')
const tiptapPkgs = fs.existsSync(path.join(crmNodeModules, '@tiptap')) 
  ? fs.readdirSync(path.join(crmNodeModules, '@tiptap')).map(d => '@tiptap/' + d) 
  : []
const pmPkgs = fs.existsSync(crmNodeModules)
  ? fs.readdirSync(crmNodeModules).filter(d => d.startsWith('prosemirror-'))
  : []

const extraAliases = {
  'frappe-ui/tailwind': path.resolve(crmNodeModules, 'frappe-ui/tailwind/preset.js'),
  'frappe-ui/style.css': path.resolve(crmNodeModules, 'frappe-ui/src/style.css'),
  'frappe-ui/frappe': path.resolve(crmNodeModules, 'frappe-ui/frappe/index.js'),
  'frappe-ui/editor': path.resolve(crmNodeModules, 'frappe-ui/src/molecules/editor/index.ts'),
  'frappe-ui/editor-style.css': path.resolve(crmNodeModules, 'frappe-ui/src/molecules/editor/style.css'),
  'frappe-ui/internals': path.resolve(crmNodeModules, 'frappe-ui/internals.ts'),
  'frappe-ui': path.resolve(crmNodeModules, 'frappe-ui'),
}

export default defineConfig({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
  },
  plugins: [
    vue({
      script: {
        fs: {
          fileExists: fs.existsSync,
          readFile: (file) => fs.readFileSync(file, 'utf-8'),
        },
      },
    }),
    vueJsx(),
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
      '@vueuse/core': path.resolve(crmNodeModules, '@vueuse/core'),
      ...extraAliases
    },
    dedupe: [
      'vue',
      'vue-router',
      'pinia',
    ],
  },
  optimizeDeps: {
    include: [
      'frappe-ui > feather-icons',
      'showdown',
      'tailwind.config.js',
      'engine.io-client',
      'highlight.js/lib/core',
      'prosemirror-state',
      'prosemirror-view',
      'lowlight',
      'interactjs',
    ],
  },
})

function getAppName() {
  return path.basename(path.resolve(__dirname, '..'))
}
