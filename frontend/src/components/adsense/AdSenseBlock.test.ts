// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest"
import { createApp, nextTick, type App } from "vue"
import AdSenseBlock from "./AdSenseBlock.vue"

type AdWindow = Window & { adsbygoogle?: object[] }
let app: App | undefined
let container: HTMLDivElement | undefined
const originalWidth = window.innerWidth

async function mount(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width })
  ;(window as AdWindow).adsbygoogle = []
  container = document.createElement("div")
  document.body.append(container)
  app = createApp(AdSenseBlock)
  app.mount(container)
  await nextTick()
  return container.querySelector("ins")!
}

afterEach(() => {
  app?.unmount()
  container?.remove()
  delete (window as AdWindow).adsbygoogle
  Object.defineProperty(window, "innerWidth", { configurable: true, value: originalWidth })
  vi.restoreAllMocks()
})

describe("AdSense banner sizing", () => {
  it("requests a compact desktop ad with the existing unit instead of cropping a tall creative", async () => {
    const ad = await mount(1000)
    expect(ad.style.height).toBe("90px")
    expect(ad.style.width).toBe("100%")
    expect(ad.style.maxWidth).toBe("970px")
    expect(ad.style.overflow).toBe("")
    expect(ad.getAttribute("data-ad-format")).toBe("fluid")
    expect(ad.getAttribute("data-ad-slot")).toBe("6796688615")
    expect(ad.hasAttribute("data-full-width-responsive")).toBe(false)
    expect((window as AdWindow).adsbygoogle).toHaveLength(1)
  })

  it("uses 100px on small screens and changes height on resize without requesting another ad", async () => {
    const ad = await mount(375)
    expect(ad.style.height).toBe("100px")
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 800 })
    window.dispatchEvent(new Event("resize"))
    await nextTick()
    expect(ad.style.height).toBe("90px")
    expect((window as AdWindow).adsbygoogle).toHaveLength(1)
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 799 })
    window.dispatchEvent(new Event("resize"))
    await nextTick()
    expect(ad.style.height).toBe("100px")
  })

  it("cleans up its resize listener when removed", async () => {
    const removeListener = vi.spyOn(window, "removeEventListener")
    await mount(1000)
    app!.unmount()
    app = undefined
    expect(removeListener).toHaveBeenCalledWith("resize", expect.any(Function))
  })
})
