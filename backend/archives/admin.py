from django.contrib import admin

from .models import ArchiveSubscription, Post, PostBlock, PostComment, PostLike


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


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "is_visible", "created_at")
    list_filter = ("is_visible", "created_at")
    search_fields = ("post__title", "user__email", "body")
    readonly_fields = ("post", "user", "body", "created_at", "updated_at")
    fields = ("post", "user", "body", "is_visible", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    search_fields = ("post__title", "user__email")
    readonly_fields = ("post", "user", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(ArchiveSubscription)
class ArchiveSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "subscribed_at", "updated_at")
    list_editable = ("is_active",)
    list_filter = ("is_active", "subscribed_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("user", "subscribed_at", "last_read_at", "updated_at")

    def has_add_permission(self, request):
        return False
