<script setup lang="ts">
import ProductCard from "./ProductCard.vue"
import { useCatalogStore } from "../../stores/catalog"

const catalog = useCatalogStore()
</script>

<template>
  <section id="catalog" class="catalog-section" aria-labelledby="catalog-title">
    <div class="section-heading">
      <div><p class="eyebrow">Curated essentials</p><h2 id="catalog-title">Popular right now</h2></div>
      <label class="category-filter">Department
        <select :value="catalog.category" @change="catalog.setCategory(($event.target as HTMLSelectElement).value)">
          <option value="">All departments</option>
          <option v-for="category in catalog.categories" :key="category.id" :value="category.slug">{{ category.name }}</option>
        </select>
      </label>
    </div>
    <div v-if="catalog.loading" class="catalog-state" aria-live="polite"><span class="loader"></span><p>Loading products…</p></div>
    <div v-else-if="catalog.error" class="catalog-state catalog-state--error" role="alert">
      <p>{{ catalog.error }}</p><button type="button" class="text-button" @click="catalog.loadProducts">Try again</button>
    </div>
    <div v-else-if="catalog.products.length" class="product-grid">
      <ProductCard v-for="product in catalog.products" :key="product.id" :product="product" />
    </div>
    <div v-else class="catalog-state"><p>No products match your search.</p><button type="button" class="text-button" @click="catalog.query = ''; catalog.category = ''; catalog.loadProducts()">Clear filters</button></div>
  </section>
</template>
