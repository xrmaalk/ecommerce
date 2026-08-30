import { onBeforeUnmount } from "vue"

export function useDebouncedFn(callback: () => void, delay = 300) {
  let timeoutId: number | undefined
  onBeforeUnmount(() => window.clearTimeout(timeoutId))
  return () => {
    window.clearTimeout(timeoutId)
    timeoutId = window.setTimeout(callback, delay)
  }
}
