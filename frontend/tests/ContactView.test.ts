// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createApp, defineComponent, h, nextTick, reactive, type App } from "vue"
import ContactView from "../src/views/ContactView.vue"
import type { BagItem } from "../src/types/bag"

const mocks = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  bag: { items: [] as BagItem[], itemCount: 0 },
  user: null,
}))
vi.mock("vue-router", () => ({ useRoute: () => mocks.route }))
vi.mock("../src/stores/auth", () => ({ useAuthStore: () => ({ user: mocks.user }) }))
vi.mock("../src/stores/bag", () => ({ useBagStore: () => mocks.bag }))

let app: App
let container: HTMLDivElement
async function flush() { await nextTick(); await Promise.resolve(); await nextTick() }
function mount() {
  container = document.createElement("div")
  document.body.append(container)
  app = createApp(ContactView)
  app.component("RouterLink", defineComponent({ setup(_, { slots }) { return () => h("a", slots.default?.()) } }))
  app.mount(container)
}
async function setValue(selector: string, value: string) {
  const element = container.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(selector)!
  element.value = value
  element.dispatchEvent(new Event(element.tagName === "SELECT" ? "change" : "input", { bubbles: true }))
  await flush()
}
async function prepare(details = "Please confirm stock for two posters.") {
  await setValue("#contact-name", "Avery Stone")
  await setValue("#contact-email", "avery@example.com")
  await setValue("#contact-details", details)
  container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))
  await flush()
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.unstubAllEnvs()
  mocks.route = reactive({ query: {} })
  mocks.bag = reactive({ items: [], itemCount: 0 })
})
afterEach(() => { app?.unmount(); container?.remove(); vi.restoreAllMocks() })

describe("Contact portal", () => {
  it("lets a guest prepare a purchase order for the fixed inbox without claiming it was sent", async () => {
    mount()
    await setValue("#contact-type", "purchase-order")
    await setValue("#contact-po", "PO-204")
    await prepare()
    const link = container.querySelector<HTMLAnchorElement>(".contact-actions a")!
    const url = new URL(link.href)
    expect(url.pathname).toBe("support@organicemperor.com")
    expect(url.searchParams.get("subject")).toContain("Purchase order request")
    expect(url.searchParams.get("body")).toContain("PO-204")
    expect(container.querySelector(".contact-preview")?.textContent).toContain("This page has not sent your request")
    expect(container.querySelector(".contact-preview")?.textContent).toContain("attach your purchase order")
    expect(document.activeElement?.id).toBe("contact-preview-title")
  })

  it("carries bag variants into the email and invalidates the draft after an edit", async () => {
    mocks.route.query.bag = "1"
    mocks.bag.items = [{ name: "Poster", slug: "poster", variation: "24x36 / Black", quantity: 2 }] as BagItem[]
    mocks.bag.itemCount = 2
    mount()
    await prepare("")
    expect(container.querySelector(".contact-item")?.textContent).toContain("24x36 / Black")
    const url = new URL(container.querySelector<HTMLAnchorElement>(".contact-actions a")!.href)
    expect(url.searchParams.get("body")).toContain("Quantity requested: 2")
    await setValue("#contact-name", "Another name")
    expect(container.querySelector(".contact-preview")).toBeNull()
  })

  it("uses the complete copy fallback for long requests", async () => {
    mount()
    const details = "Long purchase order detail. ".repeat(100) + "FINAL ITEM 99"
    await prepare(details)
    const link = container.querySelector<HTMLAnchorElement>(".contact-actions a")!
    expect(new URL(link.href).searchParams.has("body")).toBe(false)
    const text = container.querySelector<HTMLTextAreaElement>("#contact-preview-body")!.value
    expect(text).toContain("FINAL ITEM 99")
    expect(container.querySelector(".contact-preview details")?.hasAttribute("open")).toBe(true)
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } })
    container.querySelector<HTMLButtonElement>(".contact-actions button")!.click()
    await flush()
    expect(writeText).toHaveBeenCalledWith(text)
    expect(container.querySelector('[role="status"]')?.textContent).toContain("Request copied")
  })

  it("opens the text fallback if clipboard permission is unavailable", async () => {
    mount()
    await prepare()
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error("Denied")) } })
    container.querySelector<HTMLButtonElement>(".contact-actions button")!.click()
    await flush()
    expect(container.querySelector(".contact-preview details")?.hasAttribute("open")).toBe(true)
    expect(document.activeElement?.id).toBe("contact-preview-body")
    expect(container.querySelector('[role="status"]')?.textContent).toContain("Select and copy")
  })

  it("validates required fields and renders product query text without executing HTML", async () => {
    mocks.route.query = { item: '<img src=x onerror="alert(1)">', product: "poster", option: "24x36", sku: "POSTER-24", email: "wrong@example.com" }
    mount()
    expect(container.querySelector(".contact-items img")).toBeNull()
    expect(container.querySelector(".contact-items")?.textContent).toContain("<img")
    container.querySelector("form")!.dispatchEvent(new Event("submit", { cancelable: true }))
    await flush()
    expect(container.querySelector(".contact-preview")).toBeNull()
    await prepare("")
    expect(new URL(container.querySelector<HTMLAnchorElement>(".contact-actions a")!.href).pathname).toBe("support@organicemperor.com")
  })

  it("requires request text when no items are included", async () => {
    mount()
    await prepare("   ")
    expect(container.querySelector(".contact-preview")).toBeNull()
    await setValue("#contact-details", "A real enquiry")
    container.querySelector("form")!.dispatchEvent(new Event("submit", { cancelable: true }))
    await flush()
    expect(container.querySelector(".contact-preview")).not.toBeNull()
  })

  it("clears a request-text validation error when the customer includes bag items", async () => {
    mocks.bag.items = [{ name: "Poster", slug: "poster", variation: "24x36 / Black", quantity: 2 }] as BagItem[]
    mocks.bag.itemCount = 2
    mount()
    await prepare("   ")
    const details = container.querySelector<HTMLTextAreaElement>("#contact-details")!
    expect(details.validity.customError).toBe(true)
    const checkbox = container.querySelector<HTMLInputElement>('.contact-bag-choice input')!
    checkbox.checked = true
    checkbox.dispatchEvent(new Event("change", { bubbles: true }))
    await flush()
    expect(details.checkValidity()).toBe(true)
    container.querySelector("form")!.dispatchEvent(new Event("submit", { cancelable: true }))
    await flush()
    expect(container.querySelector(".contact-preview")).not.toBeNull()
  })
})
