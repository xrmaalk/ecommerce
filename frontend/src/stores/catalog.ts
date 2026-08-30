import axios from "axios"
import { defineStore } from "pinia"
import { api } from "../api/client"
import type { Category, PaginatedProducts, Product } from "../types/catalog"

export const useCatalogStore = defineStore("catalog", {
  state: () => ({
    products: [] as Product[], categories: [] as Category[], loading: false,
    error: "", query: "", category: "", requestController: null as AbortController | null,
  }),
  actions: {
    async loadCategories() {
      try {
        const { data } = await api.get<Category[] | { results: Category[] }>("/categories/")
        this.categories = Array.isArray(data) ? data : data.results
      } catch { this.categories = [] }
    },
    async loadProducts() {
      this.requestController?.abort()
      const controller = new AbortController()
      this.requestController = controller
      this.loading = true
      this.error = ""
      try {
        const { data } = await api.get<PaginatedProducts>("/products/", {
          params: { search: this.query.trim() || undefined, category: this.category || undefined },
          signal: controller.signal,
        })
        this.products = Array.isArray(data.results) ? data.results : []
      } catch (error) {
        if (!axios.isCancel(error)) this.error = "We could not load the catalogue. Please try again."
      } finally {
        if (this.requestController === controller) {
          this.loading = false
          this.requestController = null
        }
      }
    },
    setCategory(category: string) {
      this.category = category
      return this.loadProducts()
    },
  },
})
