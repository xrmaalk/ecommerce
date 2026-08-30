<script setup lang="ts">
import { computed } from "vue"
import { useThemeStore } from "../../stores/theme"

const theme = useThemeStore()
const label = computed(() => theme.current === "dark" ? "Switch to light mode" : "Switch to dark mode")
</script>

<template>
  <button type="button" class="theme-toggle" :aria-label="label" :title="label" @click="theme.toggle">
    <svg v-if="theme.current === 'dark'" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
    </svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />
    </svg>
  </button>
</template>
