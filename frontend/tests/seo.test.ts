// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"
import { articleMetadata, beginMetadata, plainText, productMetadata, safeImage, siteMetadata, sites } from "../src/seo"
import type { Product } from "../src/types/catalog"
import type { PostDetail } from "../src/archives/api"

const product = { name: "Oil", slug: "oil", short_description: "Gentle care", description: "", images: [
  { id: 1, image: "/media/front.png", alt_text: "Front", sort_order: 0 },
  { id: 2, image: "/media/back.png", alt_text: "Back", sort_order: 1 },
] } as Product
const article = { title: "Article", slug: "article", excerpt: "Public excerpt", author_name: "Editor", cover_image: "/media/cover.png", cover_alt: "Cover", published_at: "2026-10-01T12:00:00Z", updated_at: "2026-10-02T12:00:00Z", blocks: [] } as unknown as PostDetail
const content = (field: string) => document.head.querySelector(`meta[property="${field}"],meta[name="${field}"]`)?.getAttribute("content")
const canonical = () => document.head.querySelector('link[rel="canonical"]')?.getAttribute("href")

beforeEach(() => { document.head.replaceChildren() })
describe("page metadata", () => {
  it("selects the primary product image and article cover with matching canonical titles", () => {
    beginMetadata("storefront")(productMetadata(product))
    expect(content("og:image")).toBe("https://api.organicemperor.com/site/storefront/products/oil/share-image.png?v=%2Fmedia%2Ffront.png")
    expect(content("og:image:width")).toBe("1200")
    expect(content("og:image:height")).toBe("630")
    expect(content("og:image:type")).toBe("image/png")
    expect(content("og:title")).toBe("Oil")
    expect(content("twitter:image")).toBe(content("og:image"))
    expect(canonical()).toBe("https://organicemperor.com/products/oil")
    beginMetadata("archives")(articleMetadata(article))
    expect(content("og:image")).toBe("https://api.organicemperor.com/site/archives/posts/article/share-image.png?v=%2Fmedia%2Fcover.png&frame=101a16")
    expect(content("twitter:image")).toBe(content("og:image"))
    expect(content("article:author")).toBe("Editor")
    expect(content("article:published_time")).toBe(article.published_at)
    expect(content("og:type")).toBe("article")
  })

  it("removes duplicate legacy fields and preserves unrelated head elements", () => {
    for (let count = 0; count < 2; count++) {
      const meta = document.createElement("meta"); meta.setAttribute("property", "og:type"); document.head.append(meta)
    }
    const script = document.createElement("script"); script.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5910683856071010"; document.head.append(script)
    const viewport = document.createElement("meta"); viewport.name = "viewport"; viewport.content = "width=device-width"; document.head.append(viewport)
    beginMetadata("archives")(articleMetadata(article))
    beginMetadata("storefront")(productMetadata(product))
    for (const field of ["description", "author", "og:title", "og:description", "og:url", "og:type", "og:site_name", "og:image", "og:image:width", "og:image:height", "og:image:type", "og:image:alt", "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"]) {
      expect(document.head.querySelectorAll(`meta[property="${field}"],meta[name="${field}"]`)).toHaveLength(1)
    }
    expect(document.head.querySelectorAll("title,link[rel=canonical]")).toHaveLength(2)
    expect(content("article:author")).toBeUndefined()
    expect(content("author")).toBe("MK SourceCodeX")
    expect(script.isConnected && viewport.isConnected).toBe(true)
  })

  it("uses brand fallbacks, summaries, and safe text and URL handling", () => {
    const missing = articleMetadata({ ...article, excerpt: "", cover_image: "javascript:alert(1)", blocks: [{ kind: "text", text: "**Summary** [read](https://example.com) <script>bad()</script>" } as PostDetail["blocks"][number]] })
    expect(missing.image).toBe(sites.archives.image)
    expect(missing.description).toBe("Summary read")
    expect(productMetadata({ ...product, images: [], short_description: "", description: "" }).description).toBe(sites.storefront.description)
    const unsafe = productMetadata({ ...product, name: 'Oil " /><img src=x onerror=alert(1)><script>alert(2)</script>', short_description: '" /><meta name="evil"> Safe & sound' })
    beginMetadata("storefront")(unsafe)
    expect(document.head.querySelector("img,meta[name=evil]")).toBeNull()
    expect(content("og:title")).not.toContain("alert")
    expect(plainText("<p>One</p><p>two</p>")).toBe("One two")
    for (const url of ["data:image/png;base64,a", "//evil.example/a", "https://api.organicemperor.com@evil.example/a", "http://api.organicemperor.com/a", "https://evil.example/a", "https://api.organicemperor.com/a\n"]) expect(safeImage(url, "fallback")).toBe("fallback")
  })

  it("invalidates delayed updates when a newer route or listing is selected", () => {
    const old = beginMetadata("archives", "/posts/old")
    beginMetadata("archives", "/posts/article")(articleMetadata(article))
    old(articleMetadata({ ...article, title: "Old" }))
    expect(content("og:title")).toBe("Article")
    const pending = beginMetadata("archives", "/posts/pending")
    beginMetadata("archives", "/")
    pending(articleMetadata(article))
    expect(content("og:image")).toBe(sites.archives.image)
    expect(content("og:type")).toBe("website")
    expect(content("article:published_time")).toBeUndefined()
  })

  it("updates two detail pages, listing, and router back/forward", async () => {
    for (const site of ["storefront", "archives"] as const) {
      const prefix = site === "storefront" ? "products" : "posts"
      const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: {} }, { path: `/${prefix}/:slug`, component: {} }] })
      router.afterEach((to) => {
        const update = beginMetadata(site, to.path)
        if (to.params.slug) update(site === "storefront" ? productMetadata({ ...product, slug: String(to.params.slug), name: String(to.params.slug) }) : articleMetadata({ ...article, slug: String(to.params.slug), title: String(to.params.slug) }))
      })
      await router.push(`/${prefix}/first`)
      await router.push(`/${prefix}/second`)
      expect(content("og:title")).toBe("second")
      await router.push("/")
      expect(content("og:image")).toBe(sites[site].image)
      await new Promise<void>((resolve) => { const remove = router.afterEach(() => { remove(); resolve() }); router.back() })
      expect(canonical()).toBe(sites[site].origin + `/${prefix}/second`)
      await new Promise<void>((resolve) => { const remove = router.afterEach(() => { remove(); resolve() }); router.forward() })
      expect(canonical()).toBe(sites[site].origin + "/")
    }
  })
})
