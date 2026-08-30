<script setup lang="ts">
import BrandLogo from "../branding/BrandLogo.vue"
</script>

<template>
  <footer class="site-footer">
    <div class="site-footer__brand">
      <BrandLogo inverse />
      <p>Purposeful everyday care, thoughtfully selected.</p>
    </div>
    <nav aria-label="Footer navigation">
      <a href="https://organicarchives.organicemperor.com" target="_blank" rel="noopener noreferrer">Organic Archives</a>
      <RouterLink to="/privacy">Privacy</RouterLink>
      <RouterLink to="/returns">Returns</RouterLink>
    </nav>
    <p class="site-footer__credit">Powered by <a href="https://maaltech.pro" target="_blank" rel="noopener noreferrer">MAALTECH</a></p>
  </footer>
</template>
