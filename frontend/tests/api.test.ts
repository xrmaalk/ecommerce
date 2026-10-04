import { afterEach, describe, expect, it, vi } from "vitest"
import { ArchiveError, getArchive, getArchivePreview, publisherUrl } from "../src/archives/api"

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules() })
describe("Archives preview requests", () => {
  it("uses the API admin host for production publisher sessions by default", async () => {
    vi.stubEnv("DEV", false)
    vi.stubEnv("VITE_ARCHIVES_ADMIN_URL", undefined)
    vi.resetModules()
    const production = await import("../src/archives/api")
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 12, status: "draft" }) })
    vi.stubGlobal("fetch", fetch)
    expect(production.publisherUrl).toBe("https://api.organicemperor.com/admin/archives/post/")
    await production.getArchivePreview("12")
    expect(fetch).toHaveBeenCalledWith("https://api.organicemperor.com/admin/archives/post/12/preview-data/",
      expect.objectContaining({ credentials: "include", cache: "no-store", redirect: "manual" }))
  })

  it("keeps an explicitly configured admin host for installations using another publisher origin", async () => {
    vi.stubEnv("DEV", false)
    vi.stubEnv("VITE_ARCHIVES_ADMIN_URL", "https://admin.organicemperor.com/admin/archives/post/")
    vi.resetModules()
    const configured = await import("../src/archives/api")
    expect(configured.publisherUrl).toBe("https://admin.organicemperor.com/admin/archives/post/")
  })

  it("uses the configured admin origin and its session, without caching or following login redirects", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 7, status: "draft" }) })
    vi.stubGlobal("fetch", fetch)
    expect(await getArchivePreview("7")).toEqual({ id: 7, status: "draft" })
    expect(fetch).toHaveBeenCalledWith(`${publisherUrl.replace(/\/+$/, "")}/7/preview-data/`,
      expect.objectContaining({ credentials: "include", cache: "no-store", redirect: "manual" }))
    await getArchive("posts/private-release/")
    expect(fetch.mock.calls[1]![1]).toMatchObject({ credentials: "omit" })
  })
  it("reports permission errors without treating the response as article data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }))
    await expect(getArchivePreview("7")).rejects.toEqual(new ArchiveError(403))
  })
  it("recognizes a publisher login redirect as a session requirement", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ type: "opaqueredirect", ok: false, status: 0 }))
    await expect(getArchivePreview("7")).rejects.toEqual(new ArchiveError(403))
  })
})
