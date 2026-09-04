import re
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


def validate_video_size(value):
    if value.size > 100 * 1024 * 1024:
        raise ValidationError("Videos must be 100 MB or smaller.")


def video_embed_url(value):
    """Only canonical HTTPS player URLs are sent to the reader's iframe."""
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.port not in (None, 443):
        return ""
    host = parsed.hostname
    parts = parsed.path.strip("/").split("/")
    video_id = ""
    if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in ("embed", "shorts"):
            video_id = parts[1]
    elif host == "youtu.be" and len(parts) == 1:
        video_id = parts[0]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube-nocookie.com/embed/{video_id}"
    if host in ("vimeo.com", "www.vimeo.com") and len(parts) == 1 and parts[0].isdigit():
        return f"https://player.vimeo.com/video/{parts[0]}"
    if host == "player.vimeo.com" and len(parts) == 2 and parts[0] == "video" and parts[1].isdigit():
        return f"https://player.vimeo.com/video/{parts[1]}"
    return ""


class PostQuerySet(models.QuerySet):
    def public(self):
        return self.filter(status="published", published_at__lte=timezone.now())


class Post(models.Model):
    class Kind(models.TextChoices):
        ARTICLE = "article", "Article"
        RELEASE = "release", "News release"
        UPDATE = "update", "Update"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.ARTICLE)
    topic = models.CharField(max_length=60, blank=True, help_text="Optional topic, e.g. Ingredients or Behind the scenes.")
    excerpt = models.TextField(max_length=500, help_text="A short introduction for the feed and search results.")
    author_name = models.CharField(max_length=120, default="OrganicEmperor")
    cover_image = models.ImageField(upload_to="archives/covers/%Y/%m/", blank=True)
    cover_alt = models.CharField(max_length=250, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True, help_text="Required when published. A future time schedules the post automatically.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at", "-id")
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if self.status == self.Status.PUBLISHED and not self.published_at:
            errors["published_at"] = "Choose a publication date and time."
        if self.cover_image and not self.cover_alt.strip():
            errors["cover_alt"] = "Describe this image for readers using assistive technology."
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return f"https://organicarchives.organicemperor.com/posts/{self.slug}"


class PostBlock(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        HEADING = "heading", "Heading"
        QUOTE = "quote", "Quote"
        IMAGE = "image", "Image"
        VIDEO = "video", "Uploaded video"
        EMBED = "embed", "YouTube / Vimeo video"

    post = models.ForeignKey(Post, related_name="blocks", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0, help_text="Sections appear in ascending order.")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.TEXT)
    text = models.TextField(blank=True, help_text="Plain text, heading, or quote. Blank lines separate paragraphs; HTML is not rendered.")
    image = models.ImageField(upload_to="archives/images/%Y/%m/", blank=True)
    alt_text = models.CharField(max_length=250, blank=True)
    video = models.FileField(upload_to="archives/videos/%Y/%m/", blank=True,
                             validators=[FileExtensionValidator(["mp4", "webm"]), validate_video_size])
    video_url = models.URLField(blank=True, help_text="HTTPS YouTube or public Vimeo URL.")
    caption = models.CharField(max_length=300, blank=True, help_text="Image/video caption or quote attribution.")

    class Meta:
        ordering = ("position", "id")

    def clean(self):
        errors = {}
        if self.kind in (self.Kind.TEXT, self.Kind.HEADING, self.Kind.QUOTE) and not self.text.strip():
            errors["text"] = "Enter the section's text."
        if self.kind == self.Kind.IMAGE:
            if not self.image:
                errors["image"] = "Upload an image."
            if not self.alt_text.strip():
                errors["alt_text"] = "Describe the image."
        if self.kind == self.Kind.VIDEO and not self.video:
            errors["video"] = "Upload an MP4 or WebM video."
        if self.kind == self.Kind.EMBED:
            try:
                valid = video_embed_url(self.video_url)
            except ValueError:
                valid = ""
            if not valid:
                errors["video_url"] = "Use a valid HTTPS YouTube or public Vimeo video URL."
        if errors:
            raise ValidationError(errors)
