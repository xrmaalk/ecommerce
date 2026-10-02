// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createApp, defineComponent, h, nextTick, reactive, type App } from "vue"
import { AxiosError } from "axios"
import type { Product, ProductVariant } from "../src/types/catalog"
import ProductDetailView from "../src/views/ProductDetailView.vue"

const mocks = vi.hoisted(() => ({ get: vi.fn(), add: vi.fn(), open: vi.fn(), route: { params: { slug: "body-oil" } } }))
vi.mock("../src/api/client", () => ({ api: { get: mocks.get } }))
vi.mock("../src/stores/bag", () => ({ useBagStore: () => ({ add: mocks.add, open: mocks.open }) }))
vi.mock("vue-router", () => ({ useRoute: () => mocks.route }))

const product: Product = {
  id: 1, name: "Body Oil", slug: "body-oil", sku: "OIL-01",
  category: { id: 1, name: "Body care", slug: "body-care", description: "" },
  short_description: "Daily care", description: "First paragraph.\n\n<script>unsafe()</script>",
  price_cad: "20.00", compare_at_price_cad: "25.00", inventory_quantity: 3,
  in_stock: true, is_featured: true,
  images: [{ id: 1, image: "/oil-front.png", alt_text: "Front", sort_order: 0 }, { id: 2, image: "/oil-back.png", alt_text: "Back", sort_order: 1 }],
}
let app: App
let container: HTMLDivElement
const originalShowModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, "showModal")
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, "close")
async function flush() { await Promise.resolve(); await Promise.resolve(); await nextTick() }
function mount() {
  container = document.createElement("div")
  document.body.append(container)
  app = createApp(ProductDetailView)
  app.component("RouterLink", defineComponent({ setup(_, { slots }) { return () => h("a", slots.default?.()) } }))
  app.mount(container)
}
beforeEach(() => {
  vi.clearAllMocks()
  // jsdom does not implement native modal dialog behavior.
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value: function (this: HTMLDialogElement) {
    this.setAttribute("open", "")
  } })
  Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, value: function (this: HTMLDialogElement) {
    if (!this.open) return
    this.removeAttribute("open")
    this.dispatchEvent(new Event("close"))
  } })
  mocks.route = reactive({ params: { slug: "body-oil" } })
})
afterEach(() => {
  app?.unmount(); container?.remove(); vi.restoreAllMocks()
  for (const [name, descriptor] of [["showModal", originalShowModal], ["close", originalClose]] as const) {
    if (descriptor) Object.defineProperty(HTMLDialogElement.prototype, name, descriptor)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  }
})

describe("Product detail page", () => {
  it("opens the selected image in a modal, navigates photos, and restores focus on close", async () => {
    mocks.get.mockResolvedValue({ data: product })
    mount()
    await flush()
    container.querySelectorAll<HTMLButtonElement>(".product-gallery__thumbnails button")[1]!.click()
    await nextTick()
    const trigger = container.querySelector<HTMLButtonElement>(".product-gallery__expand")!
    trigger.focus()
    trigger.click()
    await nextTick()
    const dialog = document.querySelector<HTMLDialogElement>(".product-image-viewer")!
    expect(dialog.open).toBe(true)
    expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/oil-back.png")
    expect(document.body.classList.contains("product-image-viewer-open")).toBe(true)
    dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }))
    await nextTick()
    expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/oil-front.png")
    dialog.querySelector<HTMLButtonElement>('[aria-label="Previous product image"]')!.click()
    await nextTick()
    expect(dialog.querySelector("img")?.getAttribute("src")).toBe("/oil-back.png")
    dialog.querySelector<HTMLButtonElement>('[aria-label="Close full image viewer"]')!.click()
    expect(dialog.open).toBe(false)
    expect(document.activeElement).toBe(trigger)
    expect(document.body.classList.contains("product-image-viewer-open")).toBe(false)
  })

  it("closes on native Escape cancellation and clears modal state when changing products", async () => {
    mocks.get.mockResolvedValue({ data: product })
    mount()
    await flush()
    const trigger = container.querySelector<HTMLButtonElement>(".product-gallery__expand")!
    trigger.click()
    const dialog = document.querySelector<HTMLDialogElement>(".product-image-viewer")!
    dialog.dispatchEvent(new Event("cancel", { cancelable: true }))
    expect(dialog.open).toBe(false)
    trigger.click()
    expect(dialog.open).toBe(true)
    mocks.get.mockResolvedValue({ data: { ...product, slug: "tea", name: "Tea" } })
    mocks.route.params.slug = "tea"
    await flush()
    expect(document.body.classList.contains("product-image-viewer-open")).toBe(false)
    expect(document.querySelector<HTMLDialogElement>(".product-image-viewer")!.open).toBe(false)
  })
  it("requires a variation, updates its price and SKU, and passes the chosen combination to the bag", async () => {
    const variant: ProductVariant = { id: 10, sku: "LARGE-RED", size: "Large", color: "Red", label: "", name: "Size: Large / Color: Red", price_cad: "30.00", inventory_quantity: 2, track_inventory: true, in_stock: true }
    const soldOut = { ...variant, id: 11, sku: "SMALL-RED", size: "Small", in_stock: false, name: "Size: Small / Color: Red" }
    const variableProduct = { ...product, has_variants: true, variants: [variant, soldOut] }
    mocks.get.mockResolvedValue({ data: variableProduct })
    mount()
    await flush()
    const button = container.querySelector<HTMLButtonElement>(".button--primary")!
    expect(button.disabled).toBe(true)
    const select = container.querySelector<HTMLSelectElement>("select")!
    select.value = "10"
    select.dispatchEvent(new Event("change"))
    await nextTick()
    expect(button.disabled).toBe(false)
    expect(container.querySelector(".product-detail-price")?.textContent).toContain("30.00")
    expect(container.querySelector("dl")?.textContent).toContain("LARGE-RED")
    button.click()
    expect(mocks.add).toHaveBeenCalledWith(variableProduct, variant)
    select.value = "11"
    select.dispatchEvent(new Event("change"))
    await nextTick()
    expect(button.disabled).toBe(true)
    expect(button.textContent).toBe("Sold out")
  })
  it("loads a direct product URL, safely displays details, selects images, and adds the product to the bag", async () => {
    mocks.get.mockResolvedValue({ data: product })
    mount()
    await flush()
    expect(mocks.get).toHaveBeenCalledWith("/products/body-oil/", expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(container.querySelector("h1")?.textContent).toBe("Body Oil")
    expect(container.querySelector(".product-description__text")?.textContent).toContain("<script>unsafe()</script>")
    expect(container.querySelector("script")).toBeNull()
    expect(document.title).toBe("Body Oil | OrganicEmperor.com")
    const thumbnails = container.querySelectorAll<HTMLButtonElement>(".product-gallery__thumbnails button")
    thumbnails[1]!.click()
    await nextTick()
    expect(container.querySelector(".product-gallery__main img")?.getAttribute("src")).toBe("/oil-back.png")
    container.querySelector<HTMLButtonElement>(".button--primary")!.click()
    expect(mocks.add).toHaveBeenCalledWith(product)
    expect(mocks.open).toHaveBeenCalledOnce()
  })

  it("prevents adding sold-out products", async () => {
    mocks.get.mockResolvedValue({ data: { ...product, in_stock: false } })
    mount()
    await flush()
    const button = container.querySelector<HTMLButtonElement>(".button--primary")!
    expect(button.disabled).toBe(true)
    button.click()
    expect(mocks.add).not.toHaveBeenCalled()
  })

  it("shows a missing-product state for a 404", async () => {
    const error = new AxiosError("Not found")
    Object.assign(error, { response: { status: 404 } })
    mocks.get.mockRejectedValue(error)
    mount()
    await flush()
    expect(container.querySelector("h1")?.textContent).toBe("Product not found")
    expect(container.querySelector("button")).toBeNull()
    expect(container.textContent).toContain("Browse products")
  })

  it("retries temporary failures", async () => {
    mocks.get.mockRejectedValueOnce(new Error("Offline")).mockResolvedValueOnce({ data: product })
    mount()
    await flush()
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("could not load")
    container.querySelector<HTMLButtonElement>("button")!.click()
    await flush()
    expect(container.querySelector("h1")?.textContent).toBe(product.name)
  })

  it("ignores an older response after navigating to another product", async () => {
    let resolveFirst!: (value: { data: Product }) => void
    mocks.get.mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve }))
      .mockResolvedValueOnce({ data: { ...product, id: 2, slug: "tea", name: "Tea" } })
    mount()
    const firstSignal = mocks.get.mock.calls[0]![1].signal as AbortSignal
    mocks.route.params.slug = "tea"
    await flush()
    expect(firstSignal.aborted).toBe(true)
    resolveFirst({ data: product })
    await flush()
    expect(container.querySelector("h1")?.textContent).toBe("Tea")
    expect(document.title).toBe("Tea | OrganicEmperor.com")
    expect(document.head.querySelector('meta[property="og:title"]')?.getAttribute("content")).toBe("Tea")
    expect(document.head.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://organicemperor.com/products/tea")
  })

  it("retains the canonical primary sharing image when the gallery changes", async () => {
    mocks.get.mockResolvedValue({ data: product })
    mount()
    await flush()
    expect(document.head.querySelector('meta[property="og:image"]')?.getAttribute("content")).toBe("https://api.organicemperor.com/site/storefront/products/body-oil/share-image.png?v=%2Foil-front.png")
    const thumbnails = container.querySelectorAll<HTMLButtonElement>(".product-gallery__thumbnails button")
    expect(thumbnails).toHaveLength(2)
    thumbnails[1]!.click()
    await flush()
    expect(container.querySelector(".product-gallery__main img")?.getAttribute("src")).toBe("/oil-back.png")
    expect(document.head.querySelector('meta[property="og:image"]')?.getAttribute("content")).toBe("https://api.organicemperor.com/site/storefront/products/body-oil/share-image.png?v=%2Foil-front.png")
  })
})
