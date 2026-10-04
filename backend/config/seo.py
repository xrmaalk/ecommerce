"""Public metadata shells and the standalone Archives article reader."""
import hashlib
import html
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from archives.models import Post, video_embed_url
from catalog.models import Product
from .share_images import ARCHIVES_CARD_BACKGROUND

START = "<!-- page-metadata:start -->"
END = "<!-- page-metadata:end -->"
SITES = {
    "storefront": {
        "origin": "https://organicemperor.com", "name": "OrganicEmperor",
        "title": "OrganicEmperor | Forever Wellness",
        "description": "Quality body care, must have shave essentials, comforting organic teas, soap, de-odorant and wellness products.",
        "image": "https://api.organicemperor.com/site/storefront/share-image.png",
        "image_alt": "OrganicEmperor Forever Wellness featuring Purrcilla and the BODIGLO emblem in an emerald-and-gold design.",
    },
    "archives": {
        "origin": "https://organicarchives.organicemperor.com", "name": "OrganicArchives",
        "title": "OrganicArchives | OrganicEmperor",
        "description": "Articles, news releases, and updates from OrganicEmperor.com Explore the OrganicArchives.",
        "image": "https://api.organicemperor.com/site/archives/share-image.png",
        "image_alt": "OrganicArchives | OrganicEmperor",
    },
}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        elif not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value, limit=200):
    parser = PlainText()
    parser.feed(str(value or ""))
    text = "".join(parser.parts)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}[#>]+\s*", "", text)
    text = re.sub(r"[*`~]", "", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def safe_image(value, fallback):
    if not value or re.search(r"[\x00-\x20\x7f\\]", str(value)):
        return fallback
    try:
        url = urlsplit(
            urljoin(settings.SEO_MEDIA_ORIGIN.rstrip("/") + "/", str(value)))
        trusted = {site["origin"] for site in SITES.values()}
        trusted.update(settings.SEO_IMAGE_ORIGINS)
        trusted.add(settings.SEO_MEDIA_ORIGIN.rstrip("/"))
        origin = f"{url.scheme}://{url.netloc}"
        if url.scheme != "https" or url.username or url.password or origin not in trusted:
            return fallback
        return url._replace(fragment="").geturl()
    except ValueError:
        return fallback


def site_metadata(site, path="/"):
    brand = SITES[site]
    return {
        "title": brand["title"], "social_title": brand["title"],
        "description": brand["description"], "canonical": brand["origin"] + path,
        "site_name": brand["name"], "type": "website",
        "image": brand["image"], "image_alt": brand.get("image_alt", brand["name"] + " emblem"),
        "author": "MK SourceCodeX",
        "date": "2026", "modified": "2026",
        "article_author": "", "published": "2026",
    }


def share_image_url(site, kind, slug, source):
    # A changed upload has a new URL for social caches, while visibility is checked on every fetch.
    version = quote(urlsplit(source).path, safe="")
    frame = "&frame=" + ARCHIVES_CARD_BACKGROUND.lstrip("#") if site == "archives" else ""
    return f"https://api.organicemperor.com/site/{site}/{kind}/{quote(slug, safe='')}/share-image.png?v={version}{frame}"


def product_metadata(product):
    data = site_metadata("storefront", "/products/" +
                         quote(product.slug, safe=""))
    name = plain_text(product.name, 1000)
    data.update(title=f"{name} | OrganicEmperor.com", social_title=name,
                description=plain_text(product.short_description) or plain_text(product.description) or data["description"])
    # ProductImage's (sort_order, id) ordering also supplies the reader's first image.
    image = product.images.first()
    if image:
        source = safe_image(image.image.url, data["image"])
        if source != data["image"]:
            data["image"] = share_image_url(
                "storefront", "products", product.slug, source)
            data["image_alt"] = plain_text(image.alt_text) or name
    return data


def post_metadata(post):
    data = site_metadata("archives", "/posts/" + quote(post.slug, safe=""))
    title = plain_text(post.title, 1000)
    summary = plain_text(post.excerpt) or plain_text(" ".join(
        block.text for block in post.blocks.all() if block.kind in ("text", "heading", "quote")))
    data.update(title=f"{title} | OrganicArchives", social_title=title, type="article",
                description=summary or data["description"],
                author=plain_text(post.author_name) or "MK SourceCodeX",
                article_author=plain_text(post.author_name),
                published=post.published_at.isoformat() if post.published_at else "",
                modified=post.updated_at.isoformat() if post.updated_at else "")
    if post.cover_image:
        source = safe_image(post.cover_image.url, data["image"])
        if source != data["image"]:
            data["image"] = share_image_url(
                "archives", "posts", post.slug, source)
            data["image_alt"] = plain_text(post.cover_alt) or title
    return data


APP_MOUNT = '<div id="app"></div>'
ARCHIVE_READER_CSS = Path(settings.BASE_DIR) / "static" / "seo" / "archives-reader.css"


def inline_text(value):
    """Degrade inline Markdown to plain words, then escape for HTML.

    Used for server-rendered article bodies: crawlers get the words, and no
    author-supplied markup ever reaches the page unescaped.
    """
    text = str(value or "")
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = text.replace("`", "")
    return html.escape(text, quote=False)


def render_text_block(text):
    """Conservative Markdown subset (headings, lists, quotes, paragraphs)."""
    parts, list_tag, items = [], None, []

    def close_list():
        nonlocal list_tag, items
        if list_tag:
            lis = "".join(f"<li>{inline_text(item)}</li>" for item in items)
            parts.append(f"<{list_tag}>{lis}</{list_tag}>")
            list_tag, items = None, []

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_list()
            # Mirror the frontend: headings are demoted one level inside articles.
            level = min(len(heading.group(1)) + 1, 6)
            parts.append(
                f"<h{level}>{inline_text(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        ordered = re.match(r"^\d+[.)]\s+(.*)$", line)
        if bullet or ordered:
            tag = "ol" if ordered else "ul"
            if list_tag != tag:
                close_list()
                list_tag = tag
            items.append((bullet or ordered).group(1))
            continue
        close_list()
        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            parts.append(
                f"<blockquote><p>{inline_text(quote.group(1))}</p></blockquote>")
        else:
            parts.append(f"<p>{inline_text(line)}</p>")
    close_list()
    return "".join(parts)


def absolute_media_url(file_field):
    try:
        url = file_field.url
    except ValueError:
        return ""
    # Escaping an attribute does not make its URL safe. Reuse the HTTPS origin
    # allowlist used by metadata; render no media when validation fails.
    return safe_image(url, "")


def render_block(block):
    kind = block.kind
    if kind == "heading":
        text = html.escape(block.text or "", quote=False)
        return f"<h2>{text}</h2>" if text else ""
    if kind == "quote":
        text = html.escape(block.text or "", quote=False)
        if not text:
            return ""
        cite = f"<cite>{html.escape(block.caption, quote=False)}</cite>" if block.caption else ""
        return f"<blockquote><p>{text}</p>{cite}</blockquote>"
    if kind == "image":
        src = absolute_media_url(block.image)
        if not src:
            return ""
        alt = html.escape(block.alt_text or block.caption or "", quote=True)
        caption = f"<figcaption>{html.escape(block.caption, quote=False)}</figcaption>" if block.caption else ""
        return f'<figure><img src="{html.escape(src, quote=True)}" alt="{alt}" loading="lazy">{caption}</figure>'
    if kind == "video":
        src = absolute_media_url(block.video)
        caption = f"<figcaption>{html.escape(block.caption, quote=False)}</figcaption>" if block.caption else ""
        if src:
            return f'<figure><video controls preload="metadata" src="{html.escape(src, quote=True)}"></video>{caption}</figure>'
        return ""
    if kind == "embed":
        # Match the reader's YouTube/Vimeo allowlist, including old database
        # values that may have bypassed model validation. Do not fetch embeds.
        try:
            source = video_embed_url(block.video_url)
        except ValueError:
            source = ""
        if not source:
            return ""
        url = html.escape(source, quote=True)
        label = html.escape(block.caption, quote=False) or "Watch the video"
        return f'<p><a href="{url}" rel="noopener noreferrer">{label}</a></p>'
    return render_text_block(block.text) if kind == "text" else ""


def render_post_body(post):
    """Server-rendered article body.

    Crawlers and readers receive the full escaped article in the API HTML.
    The standalone reader displays this content without a frontend router.
    """
    parts = ["<article>"]
    title = post.title
    if title:
        parts.append(f"<h1>{html.escape(title, quote=False)}</h1>")
    author = post.author_name
    if author or post.published_at:
        byline = " · ".join(part for part in (author, post.published_at.date(
        ).isoformat() if post.published_at else "") if part)
        parts.append(
            f'<p class="byline">{html.escape(byline, quote=False)}</p>')
    # The head has a short summary; the body retains the complete introduction
    # and plain-text fields, just as the Vue reader does.
    excerpt = post.excerpt
    if excerpt:
        parts.append(
            f'<p class="excerpt">{html.escape(excerpt, quote=False)}</p>')
    cover = absolute_media_url(post.cover_image)
    if cover:
        parts.append(
            f'<figure class="reader-cover"><img src="{html.escape(cover, quote=True)}" alt="{html.escape(post.cover_alt, quote=True)}"></figure>')
    for block in post.blocks.all():
        rendered = render_block(block)
        if rendered:
            parts.append(rendered)
    parts.append("</article>")
    return "".join(parts)


def html_response(site, metadata, status=200, body_html="", standalone_article=False):
    try:
        shell = (Path(settings.SEO_SHELL_DIR) /
                 f"{site}.html").read_bytes().decode("utf-8")
        if shell.count(START) != 1 or shell.count(END) != 1:
            raise ValueError("Invalid metadata markers")
        if body_html and shell.count(APP_MOUNT) != 1:
            raise ValueError("Missing/duplicate article mount point")
        before, rest = shell.split(START)
        _, after = rest.split(END)
        if standalone_article:
            stylesheet_version = hashlib.sha256(ARCHIVE_READER_CSS.read_bytes()).hexdigest()[:12]
    except (OSError, ValueError):
        logging.getLogger(__name__).error(
            "Missing/invalid SEO shell for %s; package the frontend and backend together", site)
        return HttpResponse("Page unavailable" if status == 404 else "Frontend build unavailable", status=404 if status == 404 else 503)
    # Django autoescapes both attribute values and title text.
    head = render_to_string("seo/head.html", metadata)
    if standalone_article:
        # This API URL has no frontend router or /assets/ directory. Serve the
        # escaped saved article with its own stylesheet and canonical links.
        page = render_to_string("seo/archives_reader.html", {
            "head_html": head, "body_html": body_html, "missing": status == 404,
            "archives_origin": SITES["archives"]["origin"],
            "canonical": metadata["canonical"],
            "reader_css_url": reverse("seo-archives-css") + "?v=" + stylesheet_version,
        })
    else:
        # The storefront shell's scripts stay byte-for-byte intact.
        page = before + START + head + END + after
        if body_html:
            page = page.replace(APP_MOUNT, f'<div id="app">{body_html}</div>', 1)
    response = HttpResponse(page, status=status)
    if status == 404:
        response["X-Robots-Tag"] = "noindex"
    return response


@require_safe
@never_cache
def product_page(request, slug):
    product = Product.objects.filter(
        is_active=True, slug=slug).prefetch_related("images").first()
    metadata = product_metadata(product) if product else site_metadata(
        "storefront", "/products/" + quote(slug, safe=""))
    return html_response("storefront", metadata, 200 if product else 404)


@require_safe
@never_cache
def post_page(request, slug):
    post = Post.objects.public().filter(slug=slug).prefetch_related("blocks").first()
    metadata = post_metadata(post) if post else site_metadata(
        "archives", "/posts/" + quote(slug, safe=""))
    body_html = render_post_body(post) if post else ""
    return html_response("archives", metadata, 200 if post else 404, body_html, standalone_article=True)


@require_safe
def archives_reader_css(request):
    """Serve this one packaged public asset without a collectstatic dependency."""
    try:
        content = ARCHIVE_READER_CSS.read_bytes()
    except OSError:
        return HttpResponse("Stylesheet unavailable", status=404, content_type="text/plain")
    version = hashlib.sha256(content).hexdigest()[:12]
    response = HttpResponse(content, content_type="text/css; charset=utf-8")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = (
        "public, max-age=31536000, immutable" if request.GET.get("v") == version
        else "public, max-age=0, must-revalidate"
    )
    return response


ARCHIVES_ORIGIN = SITES["archives"]["origin"]


@require_safe
@never_cache
def archives_sitemap(request):
    urls = [f"<url><loc>{ARCHIVES_ORIGIN}/</loc></url>"]
    for post in Post.objects.public().only("slug", "updated_at", "published_at").order_by("-published_at", "-id").iterator():
        stamp = max(stamp for stamp in (
            post.updated_at, post.published_at) if stamp)
        lastmod = f"<lastmod>{stamp.date().isoformat()}</lastmod>" if stamp else ""
        loc = html.escape(
            f"{ARCHIVES_ORIGIN}/posts/{quote(post.slug, safe='')}", quote=True)
        urls.append(f"<url><loc>{loc}</loc>{lastmod}</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls) + "</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")


@require_safe
@never_cache
def archives_robots(request):
    return HttpResponse(
        f"User-agent: *\nAllow: /\nSitemap: {ARCHIVES_ORIGIN}/sitemap.xml\n",
        content_type="text/plain",
    )
