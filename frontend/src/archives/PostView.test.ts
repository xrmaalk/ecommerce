// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createApp, defineComponent, h, nextTick, reactive, type App } from "vue"
import { ArchiveError, type PostPreview } from "./api"
import PostView from "./PostView.vue"

const mocks = vi.hoisted(() => ({
  getArchive: vi.fn(), getPreview: vi.fn(), getEngagement: vi.fn(), initialize: vi.fn(),
  route: { name: "preview", params: { id: "7", slug: "private-release" }, fullPath: "/preview/7" },
}))
vi.mock("vue-router", () => ({ useRoute: () => mocks.route }))
vi.mock("./api", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api")>(),
  getArchive: mocks.getArchive, getArchivePreview: mocks.getPreview,
}))
vi.mock("./readerApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("./readerApi")>(), getPostEngagement: mocks.getEngagement,
}))
vi.mock("./readerStore", () => ({ useArchiveReaderStore: () => ({
  initialize: mocks.initialize, isAuthenticated: false, notifications: { unread_count: 0 },
}) }))

const draft: PostPreview = {
  id: 7, title: "A private release", slug: "private-release", kind: "release", topic: "News",
  excerpt: "Saved draft excerpt", author_name: "The editors", cover_image: "/cover.png", cover_alt: "Cover",
  published_at: null, reading_minutes: 1, has_video: true, updated_at: "2026-10-02T12:00:00Z",
  status: "draft", edit_url: "https://admin.organicemperor.com/admin/archives/post/7/change/",
  blocks: [
    { id: 1, kind: "text", text: "**Saved draft** [a link](https://example.com) <script>unsafe()</script>", image: null, alt_text: "", video: null, embed_url: "", caption: "" },
    { id: 2, kind: "image", text: "", image: "/body.png", alt_text: "Body photo", video: null, embed_url: "", caption: "Photo caption" },
    { id: 3, kind: "video", text: "", image: null, alt_text: "", video: "/clip.mp4", embed_url: "", caption: "Video caption" },
    { id: 4, kind: "embed", text: "", image: null, alt_text: "", video: null, embed_url: "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ", caption: "Embedded video" },
  ],
}
let app: App
let container: HTMLDivElement
async function flush() { await Promise.resolve(); await Promise.resolve(); await nextTick() }
function mount() {
  container = document.createElement("div")
  document.body.append(container)
  app = createApp(PostView)
  app.component("RouterLink", defineComponent({ setup(_, { slots }) { return () => h("a", slots.default?.()) } }))
  app.mount(container)
}
beforeEach(() => {
  vi.clearAllMocks()
  mocks.route = reactive({ name: "preview", params: { id: "7", slug: "private-release" }, fullPath: "/preview/7" })
  mocks.getPreview.mockResolvedValue(draft)
  mocks.getArchive.mockResolvedValue({ ...draft, published_at: "2026-10-01T12:00:00Z" })
  mocks.getEngagement.mockResolvedValue({ like_count: 0, liked: false, comment_count: 0, comments: [] })
})
afterEach(() => { app?.unmount(); container?.remove(); vi.restoreAllMocks() })

describe("Archives draft preview", () => {
  it("shows the saved draft with shared Markdown and media rendering, without reader interactions", async () => {
    mount()
    await flush()
    expect(mocks.getPreview).toHaveBeenCalledWith("7", expect.any(AbortSignal))
    expect(mocks.getArchive).not.toHaveBeenCalled()
    expect(mocks.getEngagement).not.toHaveBeenCalled()
    expect(mocks.initialize).not.toHaveBeenCalled()
    expect(container.querySelector("h1")?.textContent).toBe(draft.title)
    expect(container.querySelector(".draft-preview-notice")?.textContent).toContain("Draft preview")
    expect(container.querySelector(".back-link")?.getAttribute("href")).toBe(draft.edit_url)
    expect(container.querySelector(".post-meta")?.textContent).toContain("Not published")
    expect(container.querySelector(".markdown-block strong")?.textContent).toBe("Saved draft")
    expect(container.querySelector("script")).toBeNull()
    expect(container.querySelector(".reader-cover img")?.getAttribute("src")).toBe("/cover.png")
    expect(container.querySelector('.reader-body img')?.getAttribute("alt")).toBe("Body photo")
    expect(container.querySelector("video")?.getAttribute("src")).toBe("/clip.mp4")
    expect(container.querySelector("iframe")?.getAttribute("src")).toBe(draft.blocks[3]!.embed_url)
    expect(container.querySelector(".reader-community")).toBeNull()
  })

  it("labels scheduled posts as editorial previews and shows the selected publication date", async () => {
    mocks.getPreview.mockResolvedValue({ ...draft, status: "published", published_at: "2026-10-03T12:00:00Z" })
    mount()
    await flush()
    expect(container.querySelector(".draft-preview-notice")?.textContent).toContain("Editorial preview")
    expect(container.querySelector("time")?.getAttribute("datetime")).toBe("2026-10-03T12:00:00Z")
    expect(container.textContent).not.toContain("Invalid Date")
  })

  it("explains publisher permissions when access is denied and offers publisher login", async () => {
    mocks.getPreview.mockRejectedValue(new ArchiveError(403))
    mount()
    await flush()
    expect(container.querySelector("h1")?.textContent).toContain("Publisher access is required")
    expect(container.querySelector(".text-link")?.textContent).toContain("Publisher login")
    expect(container.querySelector("article")).toBeNull()
  })

  it("offers login and retry when the admin redirects an expired session", async () => {
    mocks.getPreview.mockRejectedValue(new TypeError("Fetch redirect blocked"))
    mount()
    await flush()
    expect(container.textContent).toContain("Sign in through Publisher login")
    expect(container.textContent).toContain("Try again")
    expect(container.querySelector("article")).toBeNull()
  })

  it("switches safely between public articles and previews when the reader component is reused", async () => {
    mount()
    await flush()
    mocks.route.name = "post"
    mocks.route.fullPath = "/posts/private-release"
    await flush()
    expect(mocks.getArchive).toHaveBeenCalledWith("posts/private-release/", expect.any(AbortSignal))
    expect(mocks.getEngagement).toHaveBeenCalledWith("private-release")
    expect(container.querySelector(".draft-preview-notice")).toBeNull()
    expect(container.querySelector(".reader-community")).not.toBeNull()
    mocks.getPreview.mockRejectedValue(new ArchiveError(403))
    mocks.route.name = "preview"
    mocks.route.fullPath = "/preview/7"
    await flush()
    expect(container.querySelector("article")).toBeNull()
    expect(container.textContent).toContain("Publisher access is required")
  })
})
