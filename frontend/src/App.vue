<script setup lang="ts">
import { onMounted } from "vue"
import { RouterView } from "vue-router"
import BagDrawer from "./components/bag/BagDrawer.vue"
import AppFooter from "./components/layout/AppFooter.vue"
import AppHeader from "./components/layout/AppHeader.vue"
import AnnouncementBar from "./components/layout/AnnouncementBar.vue"
import { useBagStore } from "./stores/bag"

const bag = useBagStore()
onMounted(() => bag.restore())
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
