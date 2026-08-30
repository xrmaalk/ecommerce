<script setup lang="ts">
defineProps<{ drawer?: boolean }>()
defineEmits<{ continue: [] }>()
</script>

<template>
  <div class="empty-bag">
    <img src="/organic-emperor-emblem.png" alt="" />
    <h2>Your bag is ready for something thoughtful.</h2>
    <p>Explore our curated essentials and add a product you love.</p>
    <button v-if="drawer" type="button" class="button button--primary" @click="$emit('continue')">Continue shopping</button>
    <RouterLink v-else class="button button--primary" :to="{ name: 'home', hash: '#catalog' }">Shop essentials</RouterLink>
  </div>
</template>
