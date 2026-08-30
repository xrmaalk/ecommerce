<script setup lang="ts">
import { computed } from "vue"
import { formatCad } from "../../composables/useCurrency"
import { useBagStore } from "../../stores/bag"
import type { Product } from "../../types/catalog"

const props = defineProps<{ product: Product }>()
const bag = useBagStore()
const price = computed(() => formatCad(Number(props.product.price_cad)))

function addProduct() {
  bag.add(props.product)
  bag.open()
}
</script>

<template>
  <article class="product-card">
    <div class="product-card__visual">
      <img
        v-if="product.images[0]"
        :src="product.images[0].image"
        :alt="product.images[0].alt_text || product.name"
        loading="lazy"
        decoding="async" />
      <div v-else class="product-card__fallback" aria-hidden="true">
        <img src="/organic-emperor-emblem.png" alt="" /><b>ORGANIC</b
        ><strong>EMPEROR</strong>
      </div>
    </div>
    <div class="product-card__content">
      <small>{{ product.category.name }}</small>
      <h3>{{ product.name }}</h3>
      <p>{{ product.short_description }}</p>
      <span
        v-if="product.is_featured"
        class="featured-flame"
        title="Featured product">
        <span aria-hidden="true">🔥</span>
        <span class="sr-only">Featured product</span>
      </span>
      <footer>
        <strong>{{ price }} <span>CAD</span></strong>
        <button type="button" :disabled="!product.in_stock" @click="addProduct">
          {{ product.in_stock ? "Add to bag" : "Sold out" }}
        </button>
      </footer>
    </div>
  </article>
</template>
