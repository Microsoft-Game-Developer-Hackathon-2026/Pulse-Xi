import { defineConfig } from 'vite'
import typescript from 'typescript'

// A small in-process TS/TSX transform keeps local development usable in
// restricted environments that prevent esbuild from spawning a subprocess.
const tsx = {
  name: 'pulse-tsx',
  enforce: 'pre',
  transform(source, id) {
    if (!/\.[jt]sx?(\?|$)/.test(id) || id.includes('/node_modules/')) return null
    return typescript.transpileModule(source, {
      fileName: id,
      compilerOptions: { target: typescript.ScriptTarget.ES2022, jsx: typescript.JsxEmit.ReactJSX, module: typescript.ModuleKind.ESNext, sourceMap: true },
    }).outputText
  },
}

export default defineConfig({
  plugins: [tsx],
  esbuild: false,
  optimizeDeps: { noDiscovery: true },
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000', '/ws': { target: 'ws://127.0.0.1:8000', ws: true } } },
})
