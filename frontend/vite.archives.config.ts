import { fileURLToPath, URL } from "node:url"
import { defineConfig, loadEnv } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig(({ mode }) => {
  const frontendDir = fileURLToPath(new URL("./", import.meta.url))
  const env = loadEnv(mode, frontendDir, "VITE_")
  const backendUrl = env.VITE_ARCHIVES_BACKEND_URL || "http://127.0.0.1:8000"
  return {
    root: fileURLToPath(new URL("./archives", import.meta.url)),
    envDir: frontendDir,
    publicDir: fileURLToPath(new URL("./public", import.meta.url)),
    plugins: [vue()],
    build: {
      outDir: fileURLToPath(new URL("./dist-archives", import.meta.url)),
      emptyOutDir: true,
    },
    server: {
      watch: {
        ignored: ["**/dist/**", "**/dist-archives/**", "**/.seo-verification/**"],
      },
      host: "127.0.0.1",
      port: 5174,
      strictPort: true,
      proxy: {
        // Preserve the Archives host so Django can validate same-origin CSRF requests.
        "/api": { target: backendUrl, changeOrigin: false },
        "/media": { target: backendUrl, changeOrigin: false },
        "/admin": { target: backendUrl, changeOrigin: false },
        "/static": { target: backendUrl, changeOrigin: false },
      },
    },
  }
})
