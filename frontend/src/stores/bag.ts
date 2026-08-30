import { computed, ref, watch } from "vue"
import { defineStore } from "pinia"
import type { BagItem } from "../types/bag"
import type { Product } from "../types/catalog"

const STORAGE_KEY = "organic-emperor-bag-v2"
const MAX_QUANTITY = 99

function isStoredItem(value: unknown): value is BagItem {
  if (!value || typeof value !== "object") return false
  const item = value as Partial<BagItem>
  return Number.isInteger(item.id) && typeof item.name === "string" &&
    typeof item.slug === "string" && Number.isFinite(item.price) &&
    typeof item.image === "string" && typeof item.imageAlt === "string" &&
    Number.isInteger(item.quantity) && Number.isInteger(item.inventoryQuantity)
}

export const useBagStore = defineStore("bag", () => {
  const items = ref<BagItem[]>([])
  const isOpen = ref(false)
  const hasRestored = ref(false)
  const statusMessage = ref("")
  const itemCount = computed(() => items.value.reduce((total, item) => total + item.quantity, 0))
  const subtotal = computed(() => items.value.reduce((total, item) => total + item.price * item.quantity, 0))
  const isEmpty = computed(() => items.value.length === 0)

  watch(items, (value) => {
    if (!hasRestored.value) return
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value)) }
    catch { /* Bag remains available for this session. */ }
  }, { deep: true })

  function restore() {
    if (hasRestored.value) return
    try {
      const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]")
      if (Array.isArray(parsed)) {
        items.value = parsed.filter(isStoredItem).map((item) => ({
          ...item,
          quantity: Math.max(1, Math.min(MAX_QUANTITY, item.quantity)),
          price: Math.max(0, item.price),
          inventoryQuantity: Math.max(0, item.inventoryQuantity),
        }))
      }
    } catch { items.value = [] }
    finally { hasRestored.value = true }
  }

  function add(product: Product) {
    const existing = items.value.find((item) => item.id === product.id)
    const stockLimit = product.inventory_quantity > 0 ? product.inventory_quantity : MAX_QUANTITY
    if (existing) existing.quantity = Math.min(existing.quantity + 1, stockLimit, MAX_QUANTITY)
    else items.value.push({
      id: product.id, name: product.name, slug: product.slug,
      price: Math.max(0, Number(product.price_cad) || 0),
      image: product.images[0]?.image ?? "", imageAlt: product.images[0]?.alt_text || product.name,
      quantity: 1, inventoryQuantity: product.inventory_quantity,
    })
    statusMessage.value = `${product.name} added to your bag.`
  }

  function setQuantity(id: number, quantity: number) {
    const item = items.value.find((entry) => entry.id === id)
    if (!item) return
    if (quantity < 1) return remove(id)
    const stockLimit = item.inventoryQuantity > 0 ? item.inventoryQuantity : MAX_QUANTITY
    item.quantity = Math.min(Math.floor(quantity), stockLimit, MAX_QUANTITY)
    statusMessage.value = `${item.name} quantity updated to ${item.quantity}.`
  }

  function increment(id: number) {
    const item = items.value.find((entry) => entry.id === id)
    if (item) setQuantity(id, item.quantity + 1)
  }
  function decrement(id: number) {
    const item = items.value.find((entry) => entry.id === id)
    if (item) setQuantity(id, item.quantity - 1)
  }
  function remove(id: number) {
    const item = items.value.find((entry) => entry.id === id)
    items.value = items.value.filter((entry) => entry.id !== id)
    if (item) statusMessage.value = `${item.name} removed from your bag.`
  }

  return {
    items, isOpen, statusMessage, itemCount, subtotal, isEmpty,
    restore, add, setQuantity, increment, decrement, remove,
    open: () => { isOpen.value = true }, close: () => { isOpen.value = false },
  }
})
