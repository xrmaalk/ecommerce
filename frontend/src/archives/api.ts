export type PostKind = "article" | "release" | "update"
export type Post = {
  id: number
  title: string
  slug: string
  kind: PostKind
  topic: string
  excerpt: string
  author_name: string
  cover_image: string | null
  cover_alt: string
  published_at: string
  reading_minutes: number
  has_video: boolean
}
export type Block = {
  id: number
  kind: "text" | "heading" | "quote" | "image" | "video" | "embed"
  text: string
  image: string | null
  alt_text: string
  video: string | null
  embed_url: string
  caption: string
}
export type PostDetail = Post & { blocks: Block[]; updated_at: string }
export type PostPreview = Omit<PostDetail, "published_at"> & {
  published_at: string | null
  status: "draft" | "published"
  edit_url: string
}
export type Page = { count: number; next: string | null; previous: string | null; results: Post[] }
export const kindLabels: Record<PostKind, string> = { article: "Article", release: "News release", update: "Update" }
export const isDemo = import.meta.env.VITE_ARCHIVES_DEMO === "true"
export const apiBase = (import.meta.env.VITE_ARCHIVES_API_BASE_URL || (import.meta.env.DEV ? "/api/v1" : "https://api.organicemperor.com/api/v1")).replace(/\/+$/, "")
export const publisherUrl = import.meta.env.VITE_ARCHIVES_ADMIN_URL || (import.meta.env.DEV
  ? "/admin/archives/post/"
  : "https://api.organicemperor.com/admin/archives/post/")

export class ArchiveError extends Error {
  constructor(public status: number) { super("Could not load the archives") }
}
export async function getArchive<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBase}/archives/${path}`, { signal, credentials: "omit", headers: { Accept: "application/json" } })
  if (!response.ok) throw new ArchiveError(response.status)
  return response.json() as Promise<T>
}
export async function getArchivePreview(id: string, signal?: AbortSignal): Promise<PostPreview> {
  // Use the same host as Publisher login: Django session cookies are host-bound.
  // Local development proxies the admin endpoint on the Archives origin.
  const response = await fetch(`${publisherUrl.replace(/\/+$/, "")}/${encodeURIComponent(id)}/preview-data/`, {
    signal, credentials: "include", cache: "no-store", redirect: "manual",
    headers: { Accept: "application/json" },
  })
  if (response.type === "opaqueredirect") throw new ArchiveError(403)
  if (!response.ok) throw new ArchiveError(response.status)
  return response.json() as Promise<PostPreview>
}
export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-CA", { month: "short", day: "numeric", year: "numeric", timeZone: "America/Edmonton" }).format(new Date(value))
}
