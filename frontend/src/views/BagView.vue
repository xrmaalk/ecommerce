<script setup lang="ts">
import BagLineItem from "../components/bag/BagLineItem.vue"
import BagSummary from "../components/bag/BagSummary.vue"
import EmptyBag from "../components/bag/EmptyBag.vue"
import { useBagStore } from "../stores/bag"

const bag = useBagStore()
</script>

<template>
  <section class="page-shell bag-page" aria-labelledby="bag-page-title">
    <header class="page-heading"><p class="eyebrow">Your selections</p><h1 id="bag-page-title">Shopping bag</h1><p v-if="!bag.isEmpty">{{ bag.itemCount }} {{ bag.itemCount === 1 ? 'item' : 'items' }} saved in your bag.</p></header>
    <EmptyBag v-if="bag.isEmpty" />
    <div v-else class="bag-layout">
      <div class="bag-list">
        <BagLineItem v-for="item in bag.items" :key="item.id" :item="item"
          @increase="bag.increment(item.id)" @decrease="bag.decrement(item.id)" @remove="bag.remove(item.id)" />
      </div>
      <BagSummary :subtotal="bag.subtotal" :item-count="bag.itemCount" />
    </div>
  </section>
</template>
