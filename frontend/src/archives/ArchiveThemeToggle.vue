<script setup lang="ts">
import { computed, watch } from "vue"
import { useThemeStore } from "../stores/theme"

const theme = useThemeStore()
const isNight = computed(() => theme.current === "dark")
watch(isNight, (night) => {
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", night ? "#101a16" : "#153f35")
}, { immediate: true })
</script>

<template>
  <button
    type="button"
    class="archive-theme-toggle"
    role="switch"
    aria-label="Night mode"
    :aria-checked="isNight"
    :title="isNight ? 'Switch to Day mode' : 'Switch to Night mode'"
    @click="theme.toggle">
    <svg v-if="isNight" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />
    </svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
    </svg>
    <span>{{ isNight ? "Night" : "Day" }}</span>
  </button>
</template>
