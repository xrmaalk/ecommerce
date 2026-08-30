<script setup lang="ts">
defineProps<{ name: string; quantity: number; disableIncrease?: boolean }>()
defineEmits<{ decrease: []; increase: [] }>()
</script>

<template>
  <div class="quantity-stepper" role="group" :aria-label="`${name} quantity`">
    <button type="button" :aria-label="`Decrease ${name} quantity`" @click="$emit('decrease')">−</button>
    <output :aria-label="`Quantity ${quantity}`">{{ quantity }}</output>
    <button type="button" :disabled="disableIncrease" :aria-label="`Increase ${name} quantity`" @click="$emit('increase')">+</button>
  </div>
</template>
