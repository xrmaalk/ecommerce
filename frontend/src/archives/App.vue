<script setup lang="ts">
import { computed, watch } from "vue"
import { useRoute } from "vue-router"
import { isDemo, publisherUrl } from "./api"
import ArchiveThemeToggle from "./ArchiveThemeToggle.vue"
import AdSenseBlock from "../components/adsense/AdSenseBlock.vue"
import { useArchiveReaderStore } from "./readerStore"

const reader = useArchiveReaderStore()
const route = useRoute()
const preview = computed(() => route.name === "preview")
watch(() => route.name, (name) => {
  if (name && name !== "preview") void reader.initialize()
}, { immediate: true })
</script>

<template>
  <div class="archives-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <div class="brand-strip">
      <span>THE OrganicEmperor JOURNAL</span
      ><a href="https://organicemperor.com"
        >Visit the store <span aria-hidden="true">↗</span></a
      >
    </div>
    <header class="archive-header">
      <RouterLink
        to="/"
        class="archive-brand"
        aria-label="OrganicArchives home">
        <img
          class="brand-logo"
          src="https://organicarchives.organicemperor.com/organic-emperor-emblem.png"
          width="52"
          height="52"
          alt="OrganicArchives emblem"
          aria-hidden="true" />

        <small>OrganicArchives</small>
      </RouterLink>
      <nav aria-label="Main navigation">
        <RouterLink
          :to="{ name: 'feed' }"
          :class="{ active: $route.name === 'feed' }"
          >The feed</RouterLink
        >
        <ArchiveThemeToggle />
        <RouterLink
          class="reader-account-link"
          :to="{ name: 'reader' }"
          :class="{ active: $route.name === 'reader' }">
          {{ reader.isAuthenticated ? "Reader account" : "Reader sign in" }}
          <span v-if="reader.notifications.unread_count" class="notification-count">
            {{ reader.notifications.unread_count }}
          </span>
        </RouterLink>
        <a class="editor-link" :href="publisherUrl"
          >Publisher login <span aria-hidden="true">↗</span></a
        >
      </nav>
      <AdSenseBlock
        v-if="route.name && !preview"
        class="archive-ad-placement"
        role="complementary"
        aria-label="Header advertisement" />
    </header>
    <div v-if="isDemo" class="demo-notice">
      LOCAL PREVIEW · Sample editorial content for reviewing the archive. These
      posts are not live.
    </div>
    <main id="main-content" tabindex="-1"><RouterView /></main>
    <footer class="archive-footer">
      <AdSenseBlock
        v-if="route.name && !preview"
        class="archive-ad-placement"
        role="complementary"
        aria-label="Footer advertisement" />
      <RouterLink to="/" class="footer-brand"
        ><img
          class="brand-logo"
          src="https://organicarchives.organicemperor.com/organic-emperor-emblem.png"
          width="52"
          height="52"
          alt="OrganicArchives emblem"
          aria-hidden="true" /><span>OrganicArchives</span></RouterLink
      >
      <p>© {{ new Date().getFullYear() }} OrganicEmperor</p>
      <a href="https://organicemperor.com/privacy">Privacy</a>
      <a href="https://organicemperor.com"
        >OrganicEmperor.com <span aria-hidden="true">↗</span></a
      >
    </footer>
  </div>
</template>
