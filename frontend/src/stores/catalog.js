import { defineStore } from "pinia";
import { api } from "../api/client";
export const useCatalogStore = defineStore("catalog", {
    state: () => ({ products: [], categories: [], loading: false, error: "", query: "", category: "" }),
    actions: {
        async loadCategories() { const { data } = await api.get("/categories/"); this.categories = Array.isArray(data) ? data : data.results; },
        async loadProducts() { this.loading = true; this.error = ""; try {
            const { data } = await api.get("/products/", { params: { search: this.query || undefined, category: this.category || undefined } });
            this.products = data.results;
        }
        catch {
            this.error = "We could not load the catalogue. Please try again.";
        }
        finally {
            this.loading = false;
        } }
    }
});
