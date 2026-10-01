<script setup lang="ts">
import { computed } from "vue"
import { formatCad } from "../../composables/useCurrency"
import { useBagStore } from "../../stores/bag"
import type { Product } from "../../types/catalog"

const props = defineProps<{ product: Product }>()
const bag = useBagStore()
const price = computed(() => formatCad(props.product.variants?.length ? Math.min(...props.product.variants.map((variant) => Number(variant.price_cad))) : Number(props.product.price_cad)))

function addProduct() {
  if (props.product.has_variants) return
  bag.add(props.product)
  bag.open()
}
</script>

<template>
  <article class="product-card">
    <RouterLink class="product-card__visual" :to="{ name: 'product-detail', params: { slug: product.slug } }" :aria-label="`View ${product.name}`">
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
    </RouterLink>
    <div class="product-card__content">
      <small>{{ product.category.name }}</small>
      <h3><RouterLink :to="{ name: 'product-detail', params: { slug: product.slug } }">{{ product.name }}</RouterLink></h3>
      <p>{{ product.short_description }}</p>
      <RouterLink class="text-link product-card__details" :to="{ name: 'product-detail', params: { slug: product.slug } }">View details<span class="sr-only"> for {{ product.name }}</span></RouterLink>
      <span
        v-if="product.is_featured"
        class="featured-flame"
        title="Featured product">
        <span aria-hidden="true">🔥</span>
        <span class="sr-only">Featured product</span>
      </span>
      <footer>
        <strong><span v-if="product.has_variants">From </span>{{ price }} <span>CAD</span></strong>
        <RouterLink v-if="product.has_variants" class="product-card__choose" :to="{ name: 'product-detail', params: { slug: product.slug } }">{{ product.in_stock ? 'Choose options' : 'View options' }}</RouterLink>
        <button v-else type="button" :disabled="!product.in_stock" @click="addProduct">
          {{ product.in_stock ? "Add to bag" : "Sold out" }}
        </button>
      </footer>
    </div>
  </article>
</template>
