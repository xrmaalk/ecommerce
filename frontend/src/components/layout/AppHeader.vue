<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useDebouncedFn } from "../../composables/useDebouncedFn"
import { useAuthStore } from "../../stores/auth"
import { useBagStore } from "../../stores/bag"
import { useCatalogStore } from "../../stores/catalog"
import BrandLogo from "../branding/BrandLogo.vue"
import ThemeToggle from "./ThemeToggle.vue"

const bag = useBagStore()
const auth = useAuthStore()
const catalog = useCatalogStore()
const route = useRoute()
const router = useRouter()
const searchLabel = computed(() => catalog.query ? `Search for ${catalog.query}` : "Search products")

async function submitSearch() {
  if (route.name !== "home") await router.push({ name: "home", hash: "#catalog" })
  await catalog.loadProducts()
}

const debouncedSearch = useDebouncedFn(() => void submitSearch())
</script>

<template>
  <header class="site-header">
    <BrandLogo />
    <form class="site-search" role="search" @submit.prevent="submitSearch">
      <label class="sr-only" for="site-search">Search the catalogue</label>
      <input id="site-search" v-model="catalog.query" type="search" maxlength="120"
        autocomplete="off" placeholder="Search body care, shave care, teas…" @input="debouncedSearch" />
      <button type="submit" :aria-label="searchLabel">Search</button>
    </form>
    <nav class="site-nav" aria-label="Primary navigation">
      <RouterLink :to="{ name: 'home', hash: '#catalog' }">Shop</RouterLink>
      <RouterLink class="account-link" :to="{ name: auth.isAuthenticated ? 'account-settings' : 'account' }"
        :aria-label="auth.isAuthenticated ? `Account for ${auth.displayName}` : 'Sign in or create an account'">
        {{ auth.isAuthenticated ? auth.displayName : "Account" }}
      </RouterLink>
      <ThemeToggle />
      <button type="button" class="bag-button" aria-haspopup="dialog" :aria-expanded="bag.isOpen" @click="bag.open">
        Bag <span v-if="bag.itemCount" class="bag-count">{{ bag.itemCount }}</span>
      </button>
    </nav>
  </header>
</template>
