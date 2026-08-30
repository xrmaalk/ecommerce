<script setup lang="ts">
import { computed } from "vue"
import { formatCad } from "../../composables/useCurrency"
import type { BagItem } from "../../types/bag"
import QuantityStepper from "./QuantityStepper.vue"

const props = defineProps<{ item: BagItem; compact?: boolean }>()
defineEmits<{ increase: []; decrease: []; remove: [] }>()
const atLimit = computed(() => props.item.inventoryQuantity > 0 && props.item.quantity >= props.item.inventoryQuantity)
</script>

<template>
  <article class="bag-line" :class="{ 'bag-line--compact': compact }">
    <div class="bag-line__image">
      <img v-if="item.image" :src="item.image" :alt="item.imageAlt" />
      <img v-else src="/organic-emperor-emblem.png" alt="" />
    </div>
    <div class="bag-line__details">
      <div><h3>{{ item.name }}</h3><p>{{ formatCad(item.price) }} <small>CAD</small></p></div>
      <div class="bag-line__actions">
        <QuantityStepper :name="item.name" :quantity="item.quantity" :disable-increase="atLimit"
          @decrease="$emit('decrease')" @increase="$emit('increase')" />
        <button type="button" class="remove-button" @click="$emit('remove')">Remove</button>
      </div>
    </div>
    <strong class="bag-line__total">{{ formatCad(item.price * item.quantity) }}</strong>
  </article>
</template>
