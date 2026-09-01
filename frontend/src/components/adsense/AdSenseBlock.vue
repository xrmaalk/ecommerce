<script setup>
import { onMounted, nextTick } from "vue"

onMounted(async () => {
  // Wait for the DOM element to fully render in the Vue instance
  await nextTick()

  try {
    // Safely trigger the AdSense array push for SPA route changes
    ;(adsbygoogle = window.adsbygoogle || []).push({})
  } catch (error) {
    console.error("AdSense failed to initialize:", error)
  }
})
</script>

<template>
  <div class="ad-container">
    <!-- Google AdSense Placeholder Element -->
    <ins
      class="adsbygoogle"
      style="display: block"
      data-ad-format="fluid"
      data-ad-layout-key="+3j+q6+1r-cm+ek"
      data-ad-client="ca-pub-5910683856071010"
      data-ad-slot="6796688615"
      data-full-width-responsive="true">
    </ins>
  </div>
</template>

<style scoped>
.ad-container {
  margin: 2rem 0;
  min-height: 100px; /* Prevents layout shifts before ad loads */
  overflow: hidden;
}
</style>
