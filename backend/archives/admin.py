from django.contrib import admin

from .models import Post, PostBlock


class PostBlockInline(admin.StackedInline):
    model = PostBlock
    extra = 1
    fields = ("position", "kind", "text", "image", "alt_text", "video", "video_url", "caption")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "published_at", "author_name")
    list_filter = ("status", "kind", "topic")
    search_fields = ("title", "excerpt", "author_name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = (PostBlockInline,)
    fieldsets = (
        ("Post", {"fields": ("title", "slug", "kind", "topic", "excerpt", "author_name")}),
        ("Cover image", {"fields": ("cover_image", "cover_alt")}),
        ("Publishing", {"fields": ("status", "published_at", "created_at", "updated_at")}),
    )
