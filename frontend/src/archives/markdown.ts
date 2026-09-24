import DOMPurify from "dompurify"
import MarkdownIt from "markdown-it"

const archivesOrigin = "https://organicarchives.organicemperor.com"
const allowedProtocols = new Set(["http:", "https:", "mailto:", "tel:"])

export function isSafeMarkdownLink(value: string) {
  const candidate = value.trim()
  if (!candidate || /[\u0000-\u001f\u007f]/.test(candidate)) return false

  try {
    return allowedProtocols.has(new URL(candidate, archivesOrigin).protocol)
  } catch {
    return false
  }
}

const markdown = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: true,
  typographer: false,
})

markdown.validateLink = isSafeMarkdownLink

const defaultLinkOpen =
  markdown.renderer.rules.link_open ??
  ((tokens, index, options, _environment, renderer) =>
    renderer.renderToken(tokens, index, options))

markdown.renderer.rules.link_open = (tokens, index, options, environment, renderer) => {
  const token = tokens[index]
  const href = String(token.attrGet("href") ?? "")

  if (/^https?:\/\//i.test(href)) {
    token.attrSet("target", "_blank")
    token.attrSet("rel", "noopener noreferrer")
  }

  return defaultLinkOpen(tokens, index, options, environment, renderer)
}

const renderNestedHeading = (
  tokens: Parameters<NonNullable<typeof markdown.renderer.rules.heading_open>>[0],
  index: number,
  options: Parameters<NonNullable<typeof markdown.renderer.rules.heading_open>>[2],
  renderer: Parameters<NonNullable<typeof markdown.renderer.rules.heading_open>>[4],
) => {
  const token = tokens[index]
  const level = Number(token.tag.slice(1))
  token.tag = `h${Math.min(level + 1, 6)}`
  return renderer.renderToken(tokens, index, options)
}

markdown.renderer.rules.heading_open = (tokens, index, options, _environment, renderer) =>
  renderNestedHeading(tokens, index, options, renderer)
markdown.renderer.rules.heading_close = (tokens, index, options, _environment, renderer) =>
  renderNestedHeading(tokens, index, options, renderer)

// Posts have dedicated image blocks with required alternative text. Markdown
// image syntax is intentionally reduced to its alt text to prevent remote
// tracking images and to keep accessibility validation server-side.
markdown.renderer.rules.image = (tokens, index) =>
  markdown.utils.escapeHtml(tokens[index].content)

DOMPurify.addHook("uponSanitizeAttribute", (_node, data) => {
  if (data.attrName === "href" && !isSafeMarkdownLink(data.attrValue)) {
    data.keepAttr = false
  }
})

export function renderMarkdown(source: string) {
  const rendered = markdown.render(source)

  return DOMPurify.sanitize(rendered, {
    ALLOWED_TAGS: [
      "a",
      "blockquote",
      "br",
      "code",
      "del",
      "em",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "hr",
      "li",
      "ol",
      "p",
      "pre",
      "strong",
      "ul",
    ],
    ALLOWED_ATTR: ["href", "rel", "target", "title"],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
  })
}
