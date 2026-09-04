<script setup lang="ts">
import { isDemo } from "./api"
</script>

<template>
  <div class="archives-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <div class="brand-strip"><span>THE ORGANIC EMPEROR JOURNAL</span><a href="https://organicemperor.com">Visit the store <span aria-hidden="true">↗</span></a></div>
    <header class="archive-header">
      <RouterLink to="/" class="archive-brand" aria-label="Organic Archives home">
        <span class="archive-monogram" aria-hidden="true">OA<span>.</span></span>
        <span class="archive-wordmark">Organic<span>Archives</span><small>BY ORGANIC EMPEROR</small></span>
      </RouterLink>
      <nav aria-label="Main navigation">
        <RouterLink :to="{ name: 'feed' }" :class="{ active: $route.name === 'feed' }">The feed</RouterLink>
        <a class="editor-link" href="https://admin.organicemperor.com/admin/archives/post/">Publisher login <span aria-hidden="true">↗</span></a>
      </nav>
    </header>
    <div v-if="isDemo" class="demo-notice">LOCAL PREVIEW · Sample editorial content for reviewing the archive. These posts are not live.</div>
    <main id="main-content" tabindex="-1"><RouterView /></main>
    <footer class="archive-footer">
      <RouterLink to="/" class="footer-brand">OA. <span>Organic Archives</span></RouterLink>
      <p>© {{ new Date().getFullYear() }} Organic Emperor</p>
      <a href="https://organicemperor.com/privacy">Privacy</a>
      <a href="https://organicemperor.com">OrganicEmperor.com <span aria-hidden="true">↗</span></a>
    </footer>
  </div>
</template>
