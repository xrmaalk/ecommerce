<script setup lang="ts">
withDefaults(defineProps<{ compact?: boolean; inverse?: boolean }>(), {
  compact: false,
  inverse: false,
})
</script>

<template>
  <RouterLink
    class="brand-logo"
    :class="{ 'brand-logo--inverse': inverse }"
    to="/"
    aria-label="OrganicEmperor.com home">
    <img src="/organic-emperor-emblem.png" alt="" width="52" height="52" />
    <span v-if="!compact">
      <small>ORGANIC</small>
      <strong>EMPEROR</strong>
    </span>
  </RouterLink>
</template>
