import { ref } from "vue"
import { defineStore } from "pinia"

export type ColorTheme = "light" | "dark"

const STORAGE_KEY = "organic-emperor-color-theme"

export const useThemeStore = defineStore("theme", () => {
  const current = ref<ColorTheme>("light")
  const initialized = ref(false)

  function apply(theme: ColorTheme) {
    current.value = theme
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
  }

  function initialize() {
    if (initialized.value) return
    let saved: string | null = null
    try { saved = window.localStorage.getItem(STORAGE_KEY) } catch { /* Use system preference. */ }
    const preferred: ColorTheme = saved === "light" || saved === "dark"
      ? saved
      : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
    apply(preferred)
    initialized.value = true
  }

  function toggle() {
    const next: ColorTheme = current.value === "dark" ? "light" : "dark"
    apply(next)
    try { window.localStorage.setItem(STORAGE_KEY, next) } catch { /* Theme still works for this visit. */ }
  }

  return { current, initialize, toggle }
})
