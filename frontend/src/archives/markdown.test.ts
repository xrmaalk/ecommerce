// @vitest-environment jsdom

import { describe, expect, it } from "vitest"

import { isSafeMarkdownLink, renderMarkdown } from "./markdown"

describe("Archives Markdown rendering", () => {
  it("renders common Markdown and working links", () => {
    const output = renderMarkdown(
      "## A heading\n\n**Bold**, *emphasis*, and [the archive](https://example.com/story).\n\n- First\n- Second",
    )

    expect(output).toContain("<h3>A heading</h3>")
    expect(output).toContain("<strong>Bold</strong>")
    expect(output).toContain("<em>emphasis</em>")
    expect(output).toContain('href="https://example.com/story"')
    expect(output).toContain('target="_blank"')
    expect(output).toContain('rel="noopener noreferrer"')
    expect(output).toContain("<ul>")
  })

  it("treats raw HTML as text instead of executable markup", () => {
    const output = renderMarkdown(
      '<script>alert("xss")</script><img src=x onerror=alert(1)><b>not HTML</b>',
    )
    const container = document.createElement("div")
    container.innerHTML = output

    expect(container.querySelector("script, img, b")).toBeNull()
    expect(container.textContent).toContain('<script>alert("xss")</script>')
    expect(container.textContent).toContain("<img src=x onerror=alert(1)>")
    expect(output).toContain("&lt;script&gt;")
    expect(output).toContain("&lt;b&gt;not HTML&lt;/b&gt;")
  })

  it("rejects script and data links while preserving safe relative links", () => {
    const output = renderMarkdown(
      "[script](javascript:alert(1)) [data](data:text/html;base64,PHNjcmlwdD4=) [relative](/posts/safe)",
    )

    expect(output).not.toContain('href="javascript:')
    expect(output).not.toContain('href="data:')
    expect(output).toContain('href="/posts/safe"')
    expect(isSafeMarkdownLink("java\nscript:alert(1)")).toBe(false)
    expect(isSafeMarkdownLink("https://organicemperor.com/about")).toBe(true)
  })

  it("does not load Markdown image URLs", () => {
    const output = renderMarkdown("![tracking pixel](https://evil.example/pixel.gif)")

    expect(output).not.toContain("<img")
    expect(output).not.toContain("evil.example")
    expect(output).toContain("tracking pixel")
  })
})
