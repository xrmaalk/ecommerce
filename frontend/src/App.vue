<script setup lang="ts">
import { onMounted, watch } from "vue"
import { RouterView } from "vue-router"
import BagDrawer from "./components/bag/BagDrawer.vue"
import AppFooter from "./components/layout/AppFooter.vue"
import AppHeader from "./components/layout/AppHeader.vue"
import AnnouncementBar from "./components/layout/AnnouncementBar.vue"
import { useAuthStore } from "./stores/auth"
import { useBagStore } from "./stores/bag"

const bag = useBagStore()
const auth = useAuthStore()
watch(() => auth.isAuthenticated, (authenticated) => {
  if (authenticated) void bag.mergeWithServer()
})
onMounted(() => {
  bag.restore()
  void auth.initialize().then(() => {
    if (auth.isAuthenticated) void bag.mergeWithServer()
  })
})
</script>

<template>
  <div class="app-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <AnnouncementBar />
    <AppHeader />
    <main id="main-content"><RouterView /></main>
    <AppFooter />
    <BagDrawer />
    <p class="sr-only" aria-live="polite" aria-atomic="true">{{ bag.statusMessage }}</p>
  </div>
</template>
