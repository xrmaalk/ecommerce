"""Public HTML shells: the same Vue application, with metadata before JavaScript."""
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from archives.models import Post
from catalog.models import Product

START = "<!-- page-metadata:start -->"
END = "<!-- page-metadata:end -->"
SITES = {
    "storefront": {
        "origin": "https://organicemperor.com", "name": "OrganicEmperor",
        "title": "OrganicEmperor | Forever Wellness",
        "description": "OrganicEmperor.com — Quality body care, must have shave essentials and comforting organic teas, soaps and wellness products.",
        "image": "https://api.organicemperor.com/site/storefront/share-image.png",
    },
    "archives": {
        "origin": "https://organicarchives.organicemperor.com", "name": "OrganicArchives",
        "title": "OrganicArchives | OrganicEmperor",
        "description": "Articles, news releases, and updates from OrganicEmperor. Explore the OrganicArchives.",
        "image": "https://api.organicemperor.com/site/archives/share-image.png",
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
        url = urlsplit(urljoin(settings.SEO_MEDIA_ORIGIN.rstrip("/") + "/", str(value)))
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
        "image": brand["image"], "image_alt": brand["name"] + " emblem",
        "author": "MK SourceCodeX",
    }


def share_image_url(site, kind, slug, source):
    # A changed upload has a new URL for social caches, while visibility is checked on every fetch.
    version = quote(urlsplit(source).path, safe="")
    return f"https://api.organicemperor.com/site/{site}/{kind}/{quote(slug, safe='')}/share-image.png?v={version}"


def product_metadata(product):
    data = site_metadata("storefront", "/products/" + quote(product.slug, safe=""))
    name = plain_text(product.name, 1000)
    data.update(title=f"{name} | OrganicEmperor.com", social_title=name,
                description=plain_text(product.short_description) or plain_text(product.description) or data["description"])
    # ProductImage's (sort_order, id) ordering also supplies the reader's first image.
    image = product.images.first()
    if image:
        source = safe_image(image.image.url, data["image"])
        if source != data["image"]:
            data["image"] = share_image_url("storefront", "products", product.slug, source)
            data["image_alt"] = plain_text(image.alt_text) or name
    return data


def post_metadata(post):
    data = site_metadata("archives", "/posts/" + quote(post.slug, safe=""))
    title = plain_text(post.title, 1000)
    summary = plain_text(post.excerpt) or plain_text(" ".join(block.text for block in post.blocks.all() if block.kind in ("text", "heading", "quote")))
    data.update(title=f"{title} | OrganicArchives", social_title=title, type="article",
                description=summary or data["description"],
                author=plain_text(post.author_name) or "MK SourceCodeX",
                article_author=plain_text(post.author_name),
                published=post.published_at.isoformat() if post.published_at else "",
                modified=post.updated_at.isoformat() if post.updated_at else "")
    if post.cover_image:
        source = safe_image(post.cover_image.url, data["image"])
        if source != data["image"]:
            data["image"] = share_image_url("archives", "posts", post.slug, source)
            data["image_alt"] = plain_text(post.cover_alt) or title
    return data


def html_response(site, metadata, status=200):
    try:
        shell = (Path(settings.SEO_SHELL_DIR) / f"{site}.html").read_text(encoding="utf-8")
        if shell.count(START) != 1 or shell.count(END) != 1:
            raise ValueError("Invalid metadata markers")
        before, rest = shell.split(START)
        _, after = rest.split(END)
    except (OSError, ValueError):
        logging.getLogger(__name__).error("Missing/invalid SEO shell for %s; package the frontend and backend together", site)
        return HttpResponse("Page unavailable" if status == 404 else "Frontend build unavailable", status=404 if status == 404 else 503)
    # Django autoescapes both attribute values and title text. Shell scripts stay byte-for-byte intact.
    head = render_to_string("seo/head.html", metadata)
    response = HttpResponse(before + START + head + END + after, status=status)
    if status == 404:
        response["X-Robots-Tag"] = "noindex"
    return response


@require_safe
@never_cache
def product_page(request, slug):
    product = Product.objects.filter(is_active=True, slug=slug).prefetch_related("images").first()
    metadata = product_metadata(product) if product else site_metadata("storefront", "/products/" + quote(slug, safe=""))
    return html_response("storefront", metadata, 200 if product else 404)


@require_safe
@never_cache
def post_page(request, slug):
    post = Post.objects.public().filter(slug=slug).prefetch_related("blocks").first()
    metadata = post_metadata(post) if post else site_metadata("archives", "/posts/" + quote(slug, safe=""))
    return html_response("archives", metadata, 200 if post else 404)
