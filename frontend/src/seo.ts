import DOMPurify from "dompurify"
import type { Product } from "./types/catalog"
import type { PostDetail } from "./archives/api"

export type Site = "storefront" | "archives"
export const sites = {
  storefront: {
    origin: "https://organicemperor.com", name: "OrganicEmperor", title: "OrganicEmperor | Forever Wellness",
    description: "Quality body care, must have shave essentials, comforting organic teas, soap, de-odorant and wellness products.",
    image: "https://api.organicemperor.com/site/storefront/share-image.png",
    imageAlt: "OrganicEmperor Forever Wellness featuring Purrcilla and the BODIGLO emblem in an emerald-and-gold design.",
  },
  archives: {
    origin: "https://organicarchives.organicemperor.com", name: "OrganicArchives", title: "OrganicArchives | OrganicEmperor",
    description: "Articles, news releases, and updates from OrganicEmperor. Explore the OrganicArchives.",
    image: "https://api.organicemperor.com/site/archives/share-image.png",
    imageAlt: "OrganicArchives emblem",
  },
} as const
export type Metadata = {
  title: string; socialTitle: string; description: string; canonical: string; siteName: string;
  type: "website" | "article"; image: string; imageAlt: string; author: string;
  articleAuthor?: string; published?: string; modified?: string;
}
const mediaOrigin = (import.meta.env.VITE_PUBLIC_MEDIA_ORIGIN || "https://api.organicemperor.com").replace(/\/+$/, "")
const imageOrigins = new Set([mediaOrigin, sites.storefront.origin, sites.archives.origin,
  ...(import.meta.env.VITE_PUBLIC_IMAGE_ORIGINS || "").split(",").map((value: string) => value.trim().replace(/\/+$/, ""))])

export function plainText(value: string | null | undefined, limit = 200) {
  const fragment = DOMPurify.sanitize((value || "").replace(/<[^>]+>/g, " $& "), {
    ALLOWED_TAGS: [], ALLOWED_ATTR: [], RETURN_DOM: true,
  })
  const text = (fragment.textContent || "")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}[#>]+\s*/gm, "").replace(/[*`~]/g, "").replace(/\s+/g, " ").trim()
  return text.length <= limit ? text : `${text.slice(0, limit - 1).trimEnd()}…`
}

export function safeImage(value: string | null | undefined, fallback: string) {
  if (!value || /[\u0000-\u0020\u007f\\]/.test(value)) return fallback
  try {
    const url = new URL(value, `${mediaOrigin}/`)
    if (url.protocol !== "https:" || url.username || url.password || !imageOrigins.has(url.origin)) return fallback
    url.hash = ""
    return url.href
  } catch { return fallback }
}

export function siteMetadata(site: Site, path = "/", title?: string): Metadata {
  const brand = sites[site]
  // The route path is appended to a fixed origin, never resolved as an external URL.
  return {
    title: title || brand.title, socialTitle: title || brand.title, description: brand.description,
    canonical: brand.origin + (path.startsWith("/") ? path.split(/[?#]/)[0] : "/"),
    siteName: brand.name, type: "website", image: brand.image,
    imageAlt: brand.imageAlt, author: "MK SourceCodeX",
  }
}

function shareImageUrl(site: Site, kind: "products" | "posts", slug: string, source: string) {
  // Match the backend Archives frame revision so old white cards are refetched.
  const frame = site === "archives" ? "&frame=101a16" : ""
  return `https://api.organicemperor.com/site/${site}/${kind}/${encodeURIComponent(slug)}/share-image.png?v=${encodeURIComponent(new URL(source).pathname)}${frame}`
}

export function productMetadata(product: Product): Metadata {
  const metadata = siteMetadata("storefront", `/products/${encodeURIComponent(product.slug)}`)
  const name = plainText(product.name, 1000)
  metadata.title = `${name} | OrganicEmperor.com`
  metadata.socialTitle = name
  metadata.description = plainText(product.short_description) || plainText(product.description) || metadata.description
  // The API orders images by (sort_order, id); gallery selection never changes this image.
  const primary = product.images[0]
  if (primary) {
    const image = safeImage(primary.image, metadata.image)
    if (image !== metadata.image) {
      metadata.imageAlt = plainText(primary.alt_text) || name
      metadata.image = shareImageUrl("storefront", "products", product.slug, image)
    }
  }
  return metadata
}

function publicDate(value: string) {
  // Preserve the public API timestamp; reject malformed values rather than inventing dates.
  return /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value)) ? value : undefined
}

export function articleMetadata(post: PostDetail): Metadata {
  const metadata = siteMetadata("archives", `/posts/${encodeURIComponent(post.slug)}`)
  const title = plainText(post.title, 1000)
  metadata.title = `${title} | OrganicArchives`
  metadata.socialTitle = title
  metadata.type = "article"
  const summary = plainText(post.excerpt) || plainText(post.blocks.filter((block) => ["text", "heading", "quote"].includes(block.kind)).map((block) => block.text).join(" "))
  metadata.description = summary || metadata.description
  const image = safeImage(post.cover_image, metadata.image)
  if (image !== metadata.image) {
    metadata.imageAlt = plainText(post.cover_alt) || title
    metadata.image = shareImageUrl("archives", "posts", post.slug, image)
  }
  metadata.articleAuthor = plainText(post.author_name) || undefined
  metadata.author = metadata.articleAuthor || metadata.author
  metadata.published = publicDate(post.published_at)
  metadata.modified = publicDate(post.updated_at)
  return metadata
}

let revision = 0
const ownedName = /^(description|author|twitter:.*)$/i
const ownedProperty = /^(og:.*|article:.*)$/i
export function applyMetadata(metadata: Metadata) {
  // Remove all owned entries, including legacy tags with incorrect name/property attributes.
  for (const element of document.head.querySelectorAll("title, meta, link")) {
    if (element.tagName === "TITLE" || ownedName.test(element.getAttribute("name") || "") ||
        ownedProperty.test(element.getAttribute("property") || "") ||
        /^(og:|article:)/i.test(element.getAttribute("name") || "") ||
        /^twitter:/i.test(element.getAttribute("property") || "") ||
        (element.tagName === "LINK" && element.getAttribute("rel")?.toLowerCase() === "canonical")) element.remove()
  }
  const title = document.createElement("title")
  title.textContent = metadata.title
  document.head.append(title)
  const canonical = document.createElement("link")
  canonical.rel = "canonical"
  canonical.href = metadata.canonical
  document.head.append(canonical)
  const tags: ["name" | "property", string, string | undefined][] = [
    ["name", "description", metadata.description], ["name", "author", metadata.author],
    ["property", "og:title", metadata.socialTitle], ["property", "og:description", metadata.description],
    ["property", "og:url", metadata.canonical], ["property", "og:type", metadata.type],
    ["property", "og:site_name", metadata.siteName], ["property", "og:image", metadata.image],
    ["property", "og:image:width", "1200"], ["property", "og:image:height", "630"],
    ["property", "og:image:type", "image/png"],
    ["property", "og:image:alt", metadata.imageAlt], ["name", "twitter:card", "summary_large_image"],
    ["name", "twitter:title", metadata.socialTitle], ["name", "twitter:description", metadata.description],
    ["name", "twitter:image", metadata.image], ["name", "twitter:image:alt", metadata.imageAlt],
    ["property", "article:author", metadata.articleAuthor], ["property", "article:published_time", metadata.published],
    ["property", "article:modified_time", metadata.modified],
  ]
  for (const [attribute, key, value] of tags) {
    if (!value) continue
    const meta = document.createElement("meta")
    meta.setAttribute(attribute, key)
    meta.content = value
    document.head.append(meta)
  }
}

export function beginMetadata(site: Site, path = "/", title?: string) {
  const current = ++revision
  applyMetadata(siteMetadata(site, path, title))
  return (metadata: Metadata) => { if (current === revision) applyMetadata(metadata) }
}
