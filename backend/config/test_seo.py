import re
import tempfile
from datetime import timedelta
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch
from xml.etree import ElementTree

from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from archives.models import Post, PostBlock
from catalog.models import Category, Product, ProductImage
from .seo import plain_text, safe_image, share_image_url


class Head(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.values = {}
        self.nodes = []
        self.in_title = False
        self.feed(html)

    def add(self, key, value):
        self.values.setdefault(key, []).append(value)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.nodes.append((tag, attrs))
        self.in_title = tag == "title"
        if tag == "meta":
            self.add(attrs.get("property") or attrs.get("name"), attrs.get("content"))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.add("canonical", attrs.get("href"))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.add("title", data)


class PublicMetadataTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        shells = root / "shells"
        shells.mkdir()
        frontend = Path(settings.BASE_DIR).parent / "frontend"
        for site, source in (("storefront", frontend / "index.html"), ("archives", frontend / "archives" / "index.html")):
            (shells / f"{site}.html").write_bytes(source.read_bytes())
        override = override_settings(SEO_SHELL_DIR=shells, MEDIA_ROOT=root / "media", ALLOWED_HOSTS=["testserver", "other.example"])
        override.enable()
        self.addCleanup(override.disable)
        category = Category.objects.create(name="Care", slug="care")
        self.product = Product.objects.create(name='Oil "calm" & care', slug="oil", sku="oil", category=category, price_cad="20", short_description="<b>Gentle</b> daily care")
        self.post = Post.objects.create(title="An article", slug="article", excerpt="Public excerpt", author_name="Editor", status=Post.Status.PUBLISHED, published_at=timezone.now() - timedelta(days=1))

    def image(self, name):
        content = BytesIO()
        Image.new("RGB", (16, 24)).save(content, format="PNG")
        return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")

    def article_nodes(self, content):
        article = re.search(r'<div id="app">(<article>.*?</article>)</div>', content, re.S)
        self.assertIsNotNone(article)
        return Head(article.group(1)).nodes

    def parsed(self, path, status=200, **kwargs):
        response = self.client.get(path, **kwargs)
        self.assertEqual(response.status_code, status)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        head = Head(response.content.decode())
        for key in ("title", "description", "canonical", "author", "og:title", "og:description", "og:url", "og:type", "og:site_name", "og:image", "og:image:width", "og:image:height", "og:image:type", "og:image:alt", "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"):
            self.assertEqual(len(head.values.get(key, [])), 1, key)
        self.assertEqual(head.values["og:image:width"], ["1200"])
        self.assertEqual(head.values["og:image:height"], ["630"])
        self.assertEqual(head.values["og:image:type"], ["image/png"])
        self.assertIn(b"ca-pub-5910683856071010", response.content)
        self.assertIn(b'name="viewport"', response.content)
        return response, head

    def test_raw_product_html_uses_reader_primary_image_and_public_origin(self):
        ProductImage.objects.create(product=self.product, image=self.image("secondary.png"), sort_order=5, alt_text="Second")
        primary = ProductImage.objects.create(product=self.product, image=self.image("primary.png"), sort_order=0, alt_text='Front "oil"')
        ProductImage.objects.create(product=self.product, image=self.image("same-order.png"), sort_order=0)
        response, head = self.parsed("/site/storefront/products/oil", HTTP_HOST="other.example")
        self.assertEqual(head.values["og:title"], [self.product.name])
        self.assertEqual(head.values["description"], ["Gentle daily care"])
        self.assertEqual(head.values["canonical"], ["https://organicemperor.com/products/oil"])
        self.assertEqual(head.values["og:image"], [share_image_url("storefront", "products", "oil", primary.image.url)])
        self.assertEqual(head.values["og:image:alt"], ['Front "oil"'])
        self.assertEqual(head.values["og:site_name"], ["OrganicEmperor"])
        self.assertEqual(head.values["author"], ["MK SourceCodeX"])
        self.assertNotIn("article:author", head.values)
        # Fetch the exact public sharing URL without authentication.
        path = urlsplit(head.values["og:image"][0]).path
        media = self.client.get(path)
        self.assertEqual(media.status_code, 200)
        self.assertEqual(media["Content-Type"], "image/png")
        self.assertIn("no-store", media["Cache-Control"])
        with Image.open(BytesIO(media.content)) as image:
            self.assertEqual(image.size, (1200, 630))
            self.assertEqual(image.getpixel((600, 315)), (0, 0, 0))
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(self.client.head("/site/storefront/products/oil").status_code, 200)
        self.assertEqual(self.client.post("/site/storefront/products/oil").status_code, 405)

    def test_raw_article_uses_cover_and_only_public_author_dates(self):
        self.post.cover_image = self.image("cover.png")
        self.post.cover_alt = "Main cover"
        self.post.save()
        _, head = self.parsed("/site/archives/posts/article")
        self.assertEqual(head.values["og:image"], [share_image_url("archives", "posts", "article", self.post.cover_image.url)])
        self.assertEqual(head.values["og:type"], ["article"])
        self.assertEqual(head.values["article:author"], ["Editor"])
        self.assertEqual(head.values["article:published_time"], [self.post.published_at.isoformat()])
        self.assertEqual(head.values["article:modified_time"], [self.post.updated_at.isoformat()])
        self.assertEqual(head.values["canonical"], ["https://organicarchives.organicemperor.com/posts/article"])
        # The changed frame has a fresh social-cache URL and the site's night green.
        self.assertIn("&frame=101a16", head.values["og:image"][0])
        self.assertEqual(head.values["twitter:image"], head.values["og:image"])
        media = self.client.get(urlsplit(head.values["og:image"][0]).path)
        self.assertEqual(media.status_code, 200)
        with Image.open(BytesIO(media.content)) as image:
            self.assertEqual(image.size, (1200, 630))
            for corner in ((0, 0), (1199, 0), (0, 629), (1199, 629)):
                self.assertEqual(image.getpixel(corner), (16, 26, 22))
            self.assertEqual(image.getpixel((600, 315)), (0, 0, 0))

    def test_fallbacks_and_plain_text_summary(self):
        self.product.short_description = ""
        self.product.description = ""
        self.product.save()
        _, head = self.parsed("/site/storefront/products/oil")
        self.assertEqual(head.values["og:image"], ["https://api.organicemperor.com/site/storefront/share-image.png"])
        self.assertIn("Quality body care", head.values["description"][0])
        self.post.excerpt = ""
        self.post.save()
        PostBlock.objects.create(post=self.post, kind="text", text="**A summary** [read](https://example.com) <script>bad()</script>")
        _, head = self.parsed("/site/archives/posts/article")
        self.assertEqual(head.values["description"], ["A summary read"])
        self.assertEqual(head.values["og:image"], ["https://api.organicemperor.com/site/archives/share-image.png"])

    def test_inactive_draft_future_undated_and_missing_content_are_404_for_staff_too(self):
        user = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(user)
        self.product.is_active = False
        self.product.save()
        response, _ = self.parsed("/site/storefront/products/oil", 404)
        self.assertNotIn(self.product.name.encode(), response.content)
        self.assertEqual(self.client.get("/site/storefront/products/oil/share-image.png").status_code, 404)
        for status, date in ((Post.Status.DRAFT, timezone.now()), (Post.Status.PUBLISHED, timezone.now() + timedelta(days=1)), (Post.Status.PUBLISHED, None)):
            self.post.status, self.post.published_at = status, date
            self.post.save()
            response, _ = self.parsed("/site/archives/posts/article", 404)
            self.assertNotIn(b"Public excerpt", response.content)
            self.assertNotIn(b'content="Editor"', response.content)
            self.assertEqual(self.client.get("/site/archives/posts/article/share-image.png").status_code, 404)
        self.parsed("/site/archives/posts/absent", 404)
        self.parsed("/site/storefront/products/absent", 404)

    def test_edits_and_withdrawal_are_immediate_without_shared_cache(self):
        self.parsed("/site/archives/posts/article")
        self.post.title = "Revised article"
        self.post.save()
        _, head = self.parsed("/site/archives/posts/article")
        self.assertEqual(head.values["og:title"], ["Revised article"])
        self.post.status = Post.Status.DRAFT
        self.post.save()
        response, _ = self.parsed("/site/archives/posts/article", 404)
        self.assertNotIn(b"Revised article", response.content)
        self.assertEqual(self.client.get("/site/archives/posts/article/share-image.png").status_code, 404)

    def test_brand_sharing_images_are_public_pngs_with_matching_dimensions(self):
        for site in ("storefront", "archives"):
            path = f"/site/{site}/share-image.png"
            response = self.client.get(path, {"url": "http://127.0.0.1/private", "width": "9000"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            with Image.open(BytesIO(response.content)) as image:
                self.assertEqual(image.size, (1200, 630))
                if site == "archives":
                    self.assertEqual(image.getpixel((0, 0)), (16, 26, 22))
            self.assertEqual(self.client.head(path).status_code, 200)
            self.assertEqual(self.client.post(path).status_code, 405)

    def test_missing_or_corrupt_images_use_brand_fallback(self):
        for source in ("missing.png", SimpleUploadedFile("corrupt.png", b"not an image")):
            self.post.cover_image = source
            self.post.save()
            response = self.client.get("/site/archives/posts/article/share-image.png")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, self.client.get("/site/archives/share-image.png").content)
        for path in ("/site/archives/posts/absent/share-image.png", "/site/storefront/products/absent/share-image.png"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_article_sharing_image_changes_when_the_cover_is_replaced(self):
        self.post.cover_image = self.image("first.png")
        self.post.save()
        _, first = self.parsed("/site/archives/posts/article")
        content = BytesIO()
        Image.new("RGB", (40, 20), "red").save(content, format="PNG")
        self.post.cover_image = SimpleUploadedFile("replacement.png", content.getvalue(), content_type="image/png")
        self.post.save()
        _, second = self.parsed("/site/archives/posts/article")
        self.assertNotEqual(first.values["og:image"], second.values["og:image"])
        response = self.client.get(urlsplit(second.values["og:image"][0]).path)
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.getpixel((600, 315)), (255, 0, 0))

    def test_untrusted_text_is_inert_and_bad_image_urls_fall_back(self):
        self.product.name = 'Oil " /><img src=x onerror=alert(1)> <script>alert(2)</script>'
        self.product.short_description = '" /><meta name="evil" content="injected"> Safe & sound'
        self.product.save()
        _, head = self.parsed("/site/storefront/products/oil")
        self.assertFalse(any(tag == "img" or attrs.get("name") == "evil" or "onerror" in attrs for tag, attrs in head.nodes))
        self.assertNotIn("alert", head.values["og:title"][0])
        fallback = "https://organicemperor.com/organic-emperor-emblem.png"
        for url in ("javascript:alert(1)", "data:image/png;base64,a", "//evil.example/a.png", "https://api.organicemperor.com@evil.example/a", "http://api.organicemperor.com/a", "https://evil.example/a", "https://api.organicemperor.com/a\n"):
            self.assertEqual(safe_image(url, fallback), fallback)
        self.assertEqual(plain_text("<p>One</p><p>two</p>"), "One two")

    def test_missing_shell_fails_closed_for_public_content(self):
        with override_settings(SEO_SHELL_DIR=Path(self.directory.name) / "missing"):
            self.assertEqual(self.client.get("/site/storefront/products/oil").status_code, 503)
            self.assertEqual(self.client.get("/site/storefront/products/absent").status_code, 404)

    def test_post_page_includes_server_rendered_article_body(self):
        PostBlock.objects.create(post=self.post, kind="heading", text="Care routine")
        PostBlock.objects.create(post=self.post, kind="text", text="**Gentle** cleansing keeps [skin](https://example.com) calm.\n\n- Step one\n- Step two")
        PostBlock.objects.create(post=self.post, kind="quote", text="Less is more", caption="Editor")
        response = self.client.get("/site/archives/posts/article")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Article text is present in the raw HTML for crawlers...
        self.assertIn("<h1>An article</h1>", content)
        self.assertIn("<h2>Care routine</h2>", content)
        self.assertIn("<p>Gentle cleansing keeps skin calm.</p>", content)
        self.assertIn("<ul><li>Step one</li><li>Step two</li></ul>", content)
        self.assertIn("<blockquote><p>Less is more</p><cite>Editor</cite></blockquote>", content)
        # ...inside the standalone reader's article container.
        self.assertIn('<div id="app"><article>', content)

    def test_post_body_escapes_untrusted_block_content(self):
        PostBlock.objects.create(post=self.post, kind="text", text='<script>alert(1)</script> "quoted"')
        PostBlock.objects.create(post=self.post, kind="heading", text="<img src=x onerror=alert(2)>")
        content = self.client.get("/site/archives/posts/article").content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", content)
        self.assertNotIn("<img src=x", content)
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", content)

    def test_post_body_absent_for_missing_posts_and_untouched_for_products(self):
        response = self.client.get("/site/archives/posts/absent")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"<article>", response.content)
        content = self.client.get("/site/storefront/products/oil").content.decode()
        self.assertNotIn("<article>", content)
        self.assertIn('<div id="app"></div>', content)

    def test_archives_sitemap_and_robots(self):
        response = self.client.get("/site/archives/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        self.assertIn("no-store", response["Cache-Control"])
        content = response.content.decode()
        self.assertIn("<loc>https://organicarchives.organicemperor.com/</loc>", content)
        self.assertIn("<loc>https://organicarchives.organicemperor.com/posts/article</loc>", content)
        self.post.status = Post.Status.DRAFT
        self.post.save()
        self.assertNotIn(b"/posts/article</loc>", self.client.get("/site/archives/sitemap.xml").content)
        robots = self.client.get("/site/archives/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("text/plain", robots["Content-Type"])
        body = robots.content.decode()
        self.assertIn("Sitemap: https://organicarchives.organicemperor.com/sitemap.xml", body)

    def test_body_rejects_unsafe_media_and_video_links_even_without_model_validation(self):
        unsafe = (
            "javascript:alert(1)", "java\nscript:alert(1)", "data:text/html,test",
            "//evil.example/clip.mp4", "http://api.organicemperor.com/clip.mp4",
            "https://api.organicemperor.com@evil.example/clip.mp4",
            "https://evil.example/clip.mp4", "https://youtube.com:bad/watch?v=aqz-KE-bpKQ",
        )
        for value in unsafe:
            with self.subTest(value=value):
                block = PostBlock.objects.create(post=self.post, kind="embed", video_url=value)
                content = self.client.get("/site/archives/posts/article").content.decode()
                nodes = self.article_nodes(content)
                self.assertFalse(any(tag == "a" and attrs.get("href") for tag, attrs in nodes))
                block.kind = "video"
                block.save()
                content = self.client.get("/site/archives/posts/article").content.decode()
                self.assertFalse(any(tag == "a" and attrs.get("href") for tag, attrs in self.article_nodes(content)))
                block.delete()
                block = PostBlock.objects.create(post=self.post, kind="image", image="unsafe.png")
                with patch("django.core.files.storage.FileSystemStorage.url", return_value=value):
                    content = self.client.get("/site/archives/posts/article").content.decode()
                self.assertFalse(any(tag == "img" for tag, _ in self.article_nodes(content)))
                block.kind = "video"
                block.video = "unsafe.mp4"
                block.save()
                with patch("django.core.files.storage.FileSystemStorage.url", return_value=value):
                    content = self.client.get("/site/archives/posts/article").content.decode()
                self.assertFalse(any(tag == "video" for tag, _ in self.article_nodes(content)))
                block.delete()

    def test_body_keeps_complete_plain_fields_and_ordered_public_media(self):
        self.post.title = 'Literal <b>title</b> & "words"'
        self.post.excerpt = "Full introduction " + "a" * 460
        self.post.cover_image = self.image("cover.png")
        self.post.cover_alt = 'Cover " /><img src=x onerror=alert(1)>'
        self.post.save()
        PostBlock.objects.create(post=self.post, position=6, kind="embed", video_url="https://youtu.be/aqz-KE-bpKQ", caption="Film & discussion")
        video = PostBlock.objects.create(post=self.post, position=5, kind="video", video=SimpleUploadedFile("clip.mp4", b"clip"), caption="The film")
        image = PostBlock.objects.create(post=self.post, position=4, kind="image", image=self.image("body.png"), alt_text='Photo " onerror="alert(2)', caption="Photo & caption")
        PostBlock.objects.create(post=self.post, position=3, kind="quote", text="**Literal quote**", caption="[Literal attribution]")
        PostBlock.objects.create(post=self.post, position=2, kind="text", text="# Nested heading\n\n1. First\n2. Second\n\n> Quoted paragraph")
        PostBlock.objects.create(post=self.post, position=1, kind="heading", text="## Literal heading")
        content = self.client.get("/site/archives/posts/article").content.decode()
        self.assertIn("<h1>Literal &lt;b&gt;title&lt;/b&gt; &amp; \"words\"</h1>", content)
        self.assertIn(self.post.excerpt, content)
        self.assertIn("<h2>## Literal heading</h2>", content)
        self.assertIn("<h2>Nested heading</h2>", content)
        self.assertIn("<ol><li>First</li><li>Second</li></ol>", content)
        self.assertIn("<blockquote><p>Quoted paragraph</p></blockquote>", content)
        self.assertIn("<p>**Literal quote**</p><cite>[Literal attribution]</cite>", content)
        self.assertLess(content.index("## Literal heading"), content.index("Nested heading"))
        nodes = self.article_nodes(content)
        images = [attrs for tag, attrs in nodes if tag == "img"]
        self.assertEqual([attrs["src"] for attrs in images], [settings.SEO_MEDIA_ORIGIN + self.post.cover_image.url, settings.SEO_MEDIA_ORIGIN + image.image.url])
        self.assertEqual([attrs["alt"] for attrs in images], [self.post.cover_alt, image.alt_text])
        self.assertFalse(any("onerror" in attrs for _, attrs in nodes))
        self.assertIn(("video", {"controls": None, "preload": "metadata", "src": settings.SEO_MEDIA_ORIGIN + video.video.url}), nodes)
        self.assertIn('href="https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"', content)
        PostBlock.objects.filter(post=self.post, kind="embed").update(video_url="https://vimeo.com/123456")
        self.assertIn(b'href="https://player.vimeo.com/video/123456"', self.client.get("/site/archives/posts/article").content)

    def test_body_is_identical_for_crawlers_and_does_not_start_the_frontend_router(self):
        PostBlock.objects.create(post=self.post, kind="text", text="Public words and {{ untrusted_template() }}")
        path = "/site/archives/posts/article"
        content = self.client.get(path, HTTP_USER_AGENT="Mozilla/5.0").content
        self.assertEqual(content, self.client.get(path, HTTP_USER_AGENT="Googlebot").content)
        nodes = Head(content.decode()).nodes
        self.assertFalse(any(tag == "script" and attrs.get("type") == "module" for tag, attrs in nodes))
        self.assertNotIn(b"/assets/", content)
        self.assertIn(b"ca-pub-5910683856071010", content)
        self.assertIn(b"{{ untrusted_template() }}", content)

    def test_api_article_stylesheet_is_same_origin_versioned_and_packaged(self):
        _, head = self.parsed("/site/archives/posts/article")
        styles = [attrs["href"] for tag, attrs in head.nodes if tag == "link" and attrs.get("rel") == "stylesheet"]
        self.assertEqual(len(styles), 1)
        self.assertRegex(styles[0], r"^/site/archives/reader\.css\?v=[a-f0-9]{12}$")
        response = self.client.get(styles[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/css; charset=utf-8")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("immutable", response["Cache-Control"])
        source = Path(settings.BASE_DIR) / "static/seo/archives-reader.css"
        self.assertEqual(response.content, source.read_bytes())
        self.assertEqual(self.client.head(styles[0]).status_code, 200)
        self.assertEqual(self.client.post(styles[0]).status_code, 405)
        self.assertNotIn("immutable", self.client.get("/site/archives/reader.css?v=old")["Cache-Control"])
        # Query parameters never select another file or expose application data.
        self.assertEqual(self.client.get("/site/archives/reader.css?file=../../.env").content, source.read_bytes())
        self.assertTrue(any(tag == "a" and attrs.get("href") == "https://organicarchives.organicemperor.com/posts/article" for tag, attrs in head.nodes))

    def test_missing_api_reader_stylesheet_fails_closed(self):
        missing = Path(self.directory.name) / "missing.css"
        with patch("config.seo.ARCHIVE_READER_CSS", missing):
            self.assertEqual(self.client.get("/site/archives/posts/article").status_code, 503)
            self.assertEqual(self.client.get("/site/archives/posts/absent").status_code, 404)
            self.assertEqual(self.client.get("/site/archives/reader.css").status_code, 404)

    def test_sitemap_contains_only_public_canonical_urls_and_valid_dates(self):
        PostBlock.objects.create(post=self.post, kind="text", text="Private body sentinel")
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        path = "/site/archives/sitemap.xml"
        root = ElementTree.fromstring(self.client.get(path, HTTP_HOST="other.example").content)
        self.assertEqual([node.text for node in root.findall("s:url/s:loc", namespace)], [
            "https://organicarchives.organicemperor.com/",
            "https://organicarchives.organicemperor.com/posts/article",
        ])
        self.assertEqual(root.find("s:url/s:lastmod", namespace).text, self.post.updated_at.date().isoformat())
        user = get_user_model().objects.create_user(username="sitemap-staff", is_staff=True)
        self.client.force_login(user)
        for status, published in ((Post.Status.DRAFT, timezone.now()), (Post.Status.PUBLISHED, None), (Post.Status.PUBLISHED, timezone.now() + timedelta(days=1))):
            self.post.status, self.post.published_at = status, published
            self.post.save()
            response = self.client.get(path)
            self.assertNotIn(b"/posts/article", response.content)
            page = self.client.get("/site/archives/posts/article")
            self.assertEqual(page.status_code, 404)
            self.assertEqual(page["X-Robots-Tag"], "noindex")
            self.assertNotIn(b"Private body sentinel", page.content)
        # A scheduled article's publication can be newer than its last edit.
        self.post.published_at = timezone.now() - timedelta(hours=1)
        self.post.save()
        Post.objects.filter(pk=self.post.pk).update(updated_at=timezone.now() - timedelta(days=2))
        root = ElementTree.fromstring(self.client.get(path).content)
        self.assertEqual(root.find("s:url/s:lastmod", namespace).text, self.post.published_at.date().isoformat())
        self.post.delete()
        self.assertNotIn(b"/posts/article", self.client.get(path).content)

    def test_crawl_endpoints_support_head_and_reject_writes(self):
        for path in ("/site/archives/sitemap.xml", "/site/archives/robots.txt"):
            with self.subTest(path=path):
                response = self.client.head(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                self.assertIn("no-store", response["Cache-Control"])
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                self.assertEqual(self.client.post(path).status_code, 405)

    def test_missing_or_duplicate_article_mount_fails_closed(self):
        source = Path(settings.SEO_SHELL_DIR) / "archives.html"
        shell = source.read_text(encoding="utf-8")
        for replacement in ('<main id="app"></main>', '<div id="app"></div><div id="app"></div>'):
            with self.subTest(replacement=replacement):
                source.write_text(shell.replace('<div id="app"></div>', replacement), encoding="utf-8")
                self.assertEqual(self.client.get("/site/archives/posts/article").status_code, 503)
