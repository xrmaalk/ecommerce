// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import type { Product, ProductVariant } from "../types/catalog"
import { useBagStore } from "./bag"

const mocks = vi.hoisted(() => ({ put: vi.fn(), post: vi.fn(), authenticated: false }))
vi.mock("../api/client", () => ({ api: { put: mocks.put, post: mocks.post }, getApiErrorMessage: () => "Unable to save this variation." }))
vi.mock("./auth", () => ({ useAuthStore: () => ({ isAuthenticated: mocks.authenticated }) }))
const small: ProductVariant = { id: 10, sku: "S-RED", size: "Small", color: "Red", label: "", name: "Size: Small / Color: Red", price_cad: "20.00", inventory_quantity: 2, track_inventory: true, in_stock: true }
const large: ProductVariant = { ...small, id: 11, sku: "L-RED", size: "Large", name: "Size: Large / Color: Red", price_cad: "30.00", inventory_quantity: 5 }
const product: Product = { id: 1, name: "Shirt", slug: "shirt", sku: "SHIRT", category: { id: 1, name: "Clothing", slug: "clothing", description: "" }, short_description: "", description: "", price_cad: "15.00", compare_at_price_cad: null, inventory_quantity: 0, track_inventory: true, in_stock: true, is_featured: false, images: [], has_variants: true, variants: [small, large] }
function serverCart(variants: ProductVariant[]) {
  return { data: { items: variants.map((variant) => ({ product, variant, quantity: 1, unit_price_cad: variant.price_cad })) } }
}
beforeEach(() => { setActivePinia(createPinia()); window.localStorage.clear(); vi.clearAllMocks(); mocks.authenticated = false })

describe("Variation bag", () => {
  it("keeps combinations separate and edits only the selected line", () => {
    const bag = useBagStore()
    bag.add(product)
    expect(bag.items).toHaveLength(0)
    bag.add(product, small)
    bag.add(product, large)
    bag.add(product, small)
    expect(bag.items).toHaveLength(2)
    expect(bag.subtotal).toBe(70)
    bag.increment("1:10")
    expect(bag.items[0]!.quantity).toBe(2)
    bag.remove("1:10")
    expect(bag.items[0]!.variantId).toBe(11)
    expect(bag.subtotal).toBe(30)
  })

  it("allows untracked stock while blocking unavailable variations", () => {
    const bag = useBagStore()
    const unlimited = { ...small, inventory_quantity: 0, track_inventory: false }
    bag.add({ ...product, variants: [unlimited] }, unlimited)
    bag.increment("1:10")
    expect(bag.items[0]!.quantity).toBe(2)
    bag.add(product, { ...large, in_stock: false })
    expect(bag.items).toHaveLength(1)
  })

  it("restores existing bags and variation identities", () => {
    const stored = { id: 1, name: "Shirt", slug: "shirt", price: 15, image: "", imageAlt: "Shirt", quantity: 2, inventoryQuantity: 4 }
    window.localStorage.setItem("organic-emperor-bag-v2", JSON.stringify([stored, { ...stored, variantId: 10, variation: small.name }]))
    const bag = useBagStore()
    bag.restore()
    expect(bag.items.map((item) => item.key)).toEqual(["1:base", "1:10"])
    expect(bag.items[1]!.variation).toBe(small.name)
  })

  it("flushes distinct variation writes before checkout without overwriting newer bag changes", async () => {
    mocks.authenticated = true
    const bag = useBagStore()
    let finishFirst!: (value: ReturnType<typeof serverCart>) => void
    mocks.put.mockImplementationOnce(() => new Promise((resolve) => { finishFirst = resolve }))
      .mockResolvedValueOnce(serverCart([small, large]))
    bag.add(product, small)
    bag.add(product, large)
    const flushed = bag.flushSync()
    await Promise.resolve()
    expect(mocks.put.mock.calls[0]![1]).toEqual({ product_id: 1, variant_id: 10, quantity: 1 })
    finishFirst(serverCart([small]))
    await flushed
    expect(mocks.put.mock.calls[1]![1]).toEqual({ product_id: 1, variant_id: 11, quantity: 1 })
    expect(bag.items.map((item) => item.variantId)).toEqual([10, 11])
    expect(bag.subtotal).toBe(50)
  })

  it("keeps failed selections visible and blocks checkout until resolved", async () => {
    mocks.authenticated = true
    mocks.put.mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValueOnce(serverCart([large]))
    const bag = useBagStore()
    bag.add(product, small)
    bag.add(product, large)
    await expect(bag.flushSync()).rejects.toThrow("Unable to save")
    expect(bag.items).toHaveLength(2)
    mocks.put.mockResolvedValueOnce(serverCart([large]))
    bag.remove("1:10")
    await bag.flushSync()
    expect(bag.syncError).toBe("")
    expect(bag.items[0]!.variantId).toBe(11)
  })
})
