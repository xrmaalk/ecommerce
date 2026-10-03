<script setup lang="ts">
import axios from "axios"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute } from "vue-router"
import { api } from "../api/client"
import { formatCad } from "../composables/useCurrency"
import { useBagStore } from "../stores/bag"
import type { Product } from "../types/catalog"
import { beginMetadata, productMetadata, siteMetadata } from "../seo"

const route = useRoute()
const bag = useBagStore()
const product = ref<Product | null>(null)
const loading = ref(true)
const error = ref("")
const notFound = ref(false)
const selectedImage = ref(0)
const imageViewer = ref<HTMLDialogElement | null>(null)
let imageTrigger: HTMLElement | null = null
const selectedVariantId = ref<number | null>(null)
const selectedVariant = computed(() => product.value?.variants?.find((variant) => variant.id === selectedVariantId.value))
const displayedPrice = computed(() => selectedVariant.value?.price_cad ?? (product.value?.has_variants && product.value.variants?.length ? String(Math.min(...product.value.variants.map((variant) => Number(variant.price_cad)))) : product.value?.price_cad ?? "0"))
const available = computed(() => product.value?.has_variants ? Boolean(selectedVariant.value?.in_stock) : Boolean(product.value?.in_stock))
const failedImages = ref(new Set<number>())
let controller: AbortController | null = null
const currentImage = computed(() => product.value?.images[selectedImage.value])
const salePrice = computed(() => {
  const value = Number(product.value?.compare_at_price_cad)
  return product.value && !product.value.has_variants && value > Number(product.value.price_cad) ? formatCad(value) : ""
})

async function loadProduct() {
  closeImageViewer()
  controller?.abort()
  const request = new AbortController()
  controller = request
  product.value = null
  selectedImage.value = 0
  selectedVariantId.value = null
  failedImages.value = new Set()
  loading.value = true
  error.value = ""
  notFound.value = false
  const path = `/products/${encodeURIComponent(String(route.params.slug))}`
  const updateMetadata = beginMetadata("storefront", path, "Product | OrganicEmperor.com")
  try {
    const { data } = await api.get<Product>(`/products/${encodeURIComponent(String(route.params.slug))}/`, { signal: request.signal })
    if (controller !== request) return
    product.value = data
    updateMetadata(productMetadata(data))
  } catch (requestError) {
    if (controller !== request || axios.isCancel(requestError)) return
    notFound.value = axios.isAxiosError(requestError) && requestError.response?.status === 404
    error.value = notFound.value ? "This product is no longer available." : "We could not load this product. Please try again."
    if (notFound.value) updateMetadata(siteMetadata("storefront", path, "Product Not Found | OrganicEmperor.com"))
  } finally {
    if (controller === request) loading.value = false
  }
}

function addProduct() {
  if (!product.value || !available.value) return
  if (selectedVariant.value) bag.add(product.value, selectedVariant.value)
  else bag.add(product.value)
  bag.open()
}

function openImageViewer() {
  if (!currentImage.value || failedImages.value.has(currentImage.value.id)) return
  if (!imageViewer.value) return
  imageTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  imageViewer.value.showModal()
  document.body.classList.add("product-image-viewer-open")
}

function closeImageViewer() {
  imageViewer.value?.close()
  document.body.classList.remove("product-image-viewer-open")
  if (imageTrigger?.isConnected) imageTrigger.focus()
  imageTrigger = null
}

function changeImage(direction: number) {
  const count = product.value?.images.length ?? 0
  if (count > 1) selectedImage.value = (selectedImage.value + direction + count) % count
}

function handleViewerKey(event: KeyboardEvent) {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault()
    changeImage(event.key === "ArrowLeft" ? -1 : 1)
  }
}

watch(() => route.params.slug, loadProduct, { immediate: true })
onBeforeUnmount(() => { controller?.abort(); closeImageViewer() })
</script>

<template>
  <section class="product-page" :aria-busy="loading">
    <nav class="product-breadcrumb" aria-label="Breadcrumb">
      <RouterLink :to="{ name: 'home', hash: '#catalog' }">Shop</RouterLink>
      <template v-if="product"><span aria-hidden="true">/</span><span aria-current="page">{{ product.name }}</span></template>
    </nav>
    <div v-if="loading" class="catalog-state" role="status"><span class="loader" aria-hidden="true"></span><p>Loading product…</p></div>
    <div v-else-if="error" class="catalog-state">
      <h1>{{ notFound ? 'Product not found' : 'Unable to load product' }}</h1>
      <p role="alert">{{ error }}</p>
      <button v-if="!notFound" type="button" class="text-button" @click="loadProduct">Try again</button>
      <RouterLink v-else class="text-link" :to="{ name: 'home', hash: '#catalog' }">Browse products</RouterLink>
    </div>
    <div v-else-if="product" class="product-detail-grid">
      <div class="product-gallery">
        <div class="product-gallery__main">
          <button v-if="currentImage && !failedImages.has(currentImage.id)" type="button" class="product-gallery__expand" :aria-label="`View full image of ${product.name}`" aria-haspopup="dialog" @click="openImageViewer">
            <img :key="currentImage.id" :src="currentImage.image" :alt="currentImage.alt_text || product.name" decoding="async" @error="failedImages.add(currentImage.id)" />
            <span class="product-gallery__expand-hint">View full image ↗</span>
          </button>
          <div v-else class="product-gallery__fallback"><img :src="'/organic-emperor-emblem.png'" alt="" /><p>Product image unavailable</p></div>
        </div>
        <div v-if="product.images.length > 1" class="product-gallery__thumbnails" role="group" aria-label="Product images">
          <button v-for="(image, index) in product.images" :key="image.id" type="button" :aria-label="`View image ${index + 1} of ${product.name}`" :aria-pressed="selectedImage === index" @click="selectedImage = index">
            <img v-if="!failedImages.has(image.id)" :src="image.image" :alt="image.alt_text || ''" loading="lazy" @error="failedImages.add(image.id)" />
            <span v-else>Image {{ index + 1 }}</span>
          </button>
        </div>
      </div>
      <div class="product-detail-copy">
        <p class="eyebrow">{{ product.category.name }}</p>
        <h1>{{ product.name }}</h1>
        <p v-if="product.is_featured" class="product-detail-featured">✦ Featured product</p>
        <p v-if="product.short_description" class="product-detail-lede">{{ product.short_description }}</p>
        <div class="product-detail-price"><strong><small v-if="product.has_variants && !selectedVariant">From </small>{{ formatCad(Number(displayedPrice)) }} <small>CAD</small></strong><del v-if="salePrice">{{ salePrice }} CAD</del></div>
        <div v-if="product.has_variants && product.variants?.length" class="product-variation-field">
          <label for="product-variation">Choose size, color or variation</label>
          <select id="product-variation" v-model="selectedVariantId">
            <option :value="null" disabled>Select an option</option>
            <option v-for="variant in product.variants" :key="variant.id" :value="variant.id">{{ variant.name }} — {{ formatCad(Number(variant.price_cad)) }} CAD{{ variant.in_stock ? '' : ' (Sold out)' }}</option>
          </select>
        </div>
        <p class="product-detail-stock" aria-live="polite">{{ product.has_variants && !selectedVariant && product.variants?.length ? 'Select an option to see availability.' : available ? 'In stock' : 'Sold out' }}</p>
        <button type="button" class="button button--primary button--wide" :disabled="!available" @click="addProduct">{{ product.has_variants && !selectedVariant && product.variants?.length ? 'Select an option' : available ? 'Add to bag' : 'Sold out' }}</button>
        <RouterLink v-if="!product.has_variants || selectedVariant" class="button button--secondary button--wide contact-order-link" :to="{ name: 'contact', query: { item: product.name, product: product.slug, option: selectedVariant?.name, sku: selectedVariant?.sku || product.sku } }">Request this item by email</RouterLink>
        <RouterLink class="text-link product-detail-back" :to="{ name: 'home', hash: '#catalog' }">Continue shopping</RouterLink>
        <section class="product-description" aria-labelledby="product-description-title">
          <h2 id="product-description-title">About this product</h2>
          <p class="product-description__text">{{ product.description || product.short_description || 'More product details are coming soon.' }}</p>
          <dl><div><dt>Department</dt><dd>{{ product.category.name }}</dd></div><div><dt>SKU</dt><dd>{{ selectedVariant?.sku || product.sku }}</dd></div></dl>
        </section>
        <RouterLink class="text-link" :to="{ name: 'returns' }">Returns information</RouterLink>
      </div>
    </div>
    <Teleport v-if="product" to="body">
      <dialog ref="imageViewer" class="product-image-viewer" aria-labelledby="product-image-viewer-title" @cancel.prevent="closeImageViewer" @close="closeImageViewer" @click.self="closeImageViewer" @keydown="handleViewerKey">
        <header>
          <h2 id="product-image-viewer-title">{{ product.name }}</h2>
          <button type="button" aria-label="Close full image viewer" autofocus @click="closeImageViewer">Close ×</button>
        </header>
        <div class="product-image-viewer__image" @click.self="closeImageViewer">
          <img v-if="currentImage && !failedImages.has(currentImage.id)" :key="currentImage.id" :src="currentImage.image" :alt="currentImage.alt_text || product.name" @error="failedImages.add(currentImage.id)" />
          <p v-else>Product image unavailable</p>
        </div>
        <footer>
          <button v-if="product.images.length > 1" type="button" aria-label="Previous product image" @click="changeImage(-1)">← Previous</button>
          <p aria-live="polite">Image {{ selectedImage + 1 }} of {{ product.images.length }}<span v-if="currentImage?.alt_text"> · {{ currentImage.alt_text }}</span></p>
          <button v-if="product.images.length > 1" type="button" aria-label="Next product image" @click="changeImage(1)">Next →</button>
        </footer>
      </dialog>
    </Teleport>
  </section>
</template>
