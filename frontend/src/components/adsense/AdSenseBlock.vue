<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"

const bannerHeight = ref(window.innerWidth >= 800 ? 90 : 100)
// Set the height on the ad itself, as supported by AdSense for In-feed units.
// A wrapper max-height would only crop the creative after Google renders it.
const bannerStyle = computed(() => ({
  display: "block",
  width: "100%",
  maxWidth: "970px",
  height: `${bannerHeight.value}px`,
  margin: "0 auto",
}))

function updateBannerHeight() {
  bannerHeight.value = window.innerWidth >= 800 ? 90 : 100
}

onMounted(async () => {
  window.addEventListener("resize", updateBannerHeight)
  // Wait for the DOM element to fully render in the Vue instance
  await nextTick()

  try {
    // Each mounted block queues its own ad, even before the async script loads.
    const adWindow = window as Window & { adsbygoogle?: object[] }
    ;(adWindow.adsbygoogle = adWindow.adsbygoogle || []).push({})
  } catch (error) {
    console.error("AdSense failed to initialize:", error)
  }
})

onBeforeUnmount(() => window.removeEventListener("resize", updateBannerHeight))
</script>

<template>
  <div class="ad-container">
    <!-- Google AdSense Placeholder Element -->
    <ins
      class="adsbygoogle"
      :style="bannerStyle"
      data-ad-format="fluid"
      data-ad-layout-key="+3j+q6+1r-cm+ek"
      data-ad-client="ca-pub-5910683856071010"
      data-ad-slot="6796688615">
    </ins>
  </div>
</template>

<style scoped>
.ad-container {
  width: 100%;
  min-width: 0;
  margin: 1rem 0;
}
</style>
