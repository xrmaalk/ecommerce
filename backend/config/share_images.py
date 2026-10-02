"""Public sharing cards retain the entire stored image inside a wide canvas."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from archives.models import Post
from catalog.models import Product

WIDTH, HEIGHT = 1200, 630
PADDING = 48
MAX_PIXELS = 25_000_000
MAX_BYTES = 20 * 1024 * 1024
BRANDS = {
    "storefront": ("organic-emperor-emblem.png", "#09291f"),
    "archives": ("OA-Emblem-BBG.png", "#000000"),
}


def render_card(source, background):
    with Image.open(source) as original:
        if original.width * original.height > MAX_PIXELS:
            raise ValueError("Sharing source exceeds the pixel limit")
        # Use the first frame, correct camera orientation, and preserve transparency.
        image = ImageOps.exif_transpose(original).convert("RGBA")
    image = ImageOps.contain(image, (WIDTH - 2 * PADDING, HEIGHT - 2 * PADDING), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), background)
    canvas.paste(image, ((WIDTH - image.width) // 2, (HEIGHT - image.height) // 2), image)
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


@require_safe
@never_cache
def share_image(request, site, slug=None):
    image = None
    if slug is not None:
        if site == "storefront":
            item = Product.objects.filter(is_active=True, slug=slug).prefetch_related("images").first()
            primary = item.images.first() if item else None
            image = primary.image if primary else None
        else:
            item = Post.objects.public().filter(slug=slug).first()
            image = item.cover_image if item else None
        if item is None:
            return HttpResponse("Image unavailable", status=404)
    content = None
    if image:
        try:
            if image.size > MAX_BYTES:
                raise ValueError("Sharing source exceeds the byte limit")
            # Open only the model's storage file; never fetch a client-supplied URL.
            with image.open("rb") as source:
                content = render_card(source, "#ffffff")
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            pass  # Missing/corrupt/oversized media uses the same safe brand fallback.
    if content is None:
        filename, background = BRANDS[site]
        try:
            with (Path(settings.BASE_DIR) / "static" / "admin" / "img" / filename).open("rb") as source:
                content = render_card(source, background)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            return HttpResponse("Image unavailable", status=503)
    return HttpResponse(content, content_type="image/png")
