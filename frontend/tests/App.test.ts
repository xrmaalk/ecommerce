// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest"
import { createApp, defineComponent, h, nextTick, reactive } from "vue"
import App from "../src/archives/App.vue"

const mocks = vi.hoisted(() => ({
  initialize: vi.fn(), route: { name: undefined as string | undefined },
}))
vi.mock("vue-router", () => ({ useRoute: () => mocks.route }))
vi.mock("../src/archives/readerStore", () => ({ useArchiveReaderStore: () => ({
  initialize: mocks.initialize, isAuthenticated: false, notifications: { unread_count: 0 },
}) }))
vi.mock("../src/archives/ArchiveThemeToggle.vue", () => ({ default: { template: "<button>Theme</button>" } }))
vi.mock("../src/components/adsense/AdSenseBlock.vue", () => ({ default: { template: '<aside class="test-ad" />' } }))

describe("Archives preview shell", () => {
  it("waits for the route and keeps reader initialization and adverts out of previews", async () => {
    mocks.route = reactive({ name: undefined as string | undefined })
    const container = document.createElement("div")
    const app = createApp(App)
    app.component("RouterLink", defineComponent({ setup(_, { slots }) { return () => h("a", slots.default?.()) } }))
    app.component("RouterView", { template: "<div />" })
    Object.defineProperty(app.config.globalProperties, "$route", { get: () => mocks.route })
    app.mount(container)
    try {
      expect(mocks.initialize).not.toHaveBeenCalled()
      expect(container.querySelectorAll(".test-ad")).toHaveLength(0)
      mocks.route.name = "preview"
      await nextTick()
      expect(mocks.initialize).not.toHaveBeenCalled()
      expect(container.querySelectorAll(".test-ad")).toHaveLength(0)
      mocks.route.name = "post"
      await nextTick()
      expect(mocks.initialize).toHaveBeenCalledOnce()
      expect(container.querySelectorAll(".test-ad")).toHaveLength(2)
      mocks.route.name = "preview"
      await nextTick()
      expect(mocks.initialize).toHaveBeenCalledOnce()
      expect(container.querySelectorAll(".test-ad")).toHaveLength(0)
    } finally {
      app.unmount()
    }
  })
})
