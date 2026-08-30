<script setup lang="ts">
import { onMounted } from "vue"
import CatalogSection from "../components/catalog/CatalogSection.vue"
import HeroSection from "../components/catalog/HeroSection.vue"
import { useCatalogStore } from "../stores/catalog"

const catalog = useCatalogStore()
onMounted(() => Promise.all([catalog.loadCategories(), catalog.loadProducts()]))
</script>

<template><HeroSection /><CatalogSection /></template>
