import { afterEach, describe, expect, it, vi } from "vitest"
import { ArchiveError, getArchive, getArchivePreview, publisherUrl } from "./api"

afterEach(() => { vi.unstubAllGlobals() })
describe("Archives preview requests", () => {
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
