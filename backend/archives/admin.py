from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils import timezone
from django.views.decorators.http import require_safe

from .models import ArchiveSubscription, Post, PostBlock, PostComment, PostLike
from .serializers import PostDetailSerializer


class PostBlockInline(admin.StackedInline):
    model = PostBlock
    extra = 1
    fields = ("position", "kind", "text", "image", "alt_text", "video", "video_url", "caption")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "published_at", "author_name", "preview_link")
    list_filter = ("status", "kind", "topic")
    search_fields = ("title", "excerpt", "author_name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "preview_link")
    inlines = (PostBlockInline,)
    fieldsets = (
        ("Post", {"fields": ("title", "slug", "kind", "topic", "excerpt", "author_name")}),
        ("Cover image", {"fields": ("cover_image", "cover_alt")}),
        ("Publishing", {"fields": ("status", "published_at", "preview_link", "created_at", "updated_at")}),
    )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/preview-data/",
                self.admin_site.admin_view(self.preview_data),
                name="archives_post_preview_data",
            ),
        ] + super().get_urls()

    def preview_url(self, obj):
        return f"{settings.ARCHIVES_FRONTEND_URL.rstrip('/')}/preview/{obj.pk}"

    def view_on_site(self, obj):
        if obj.status == Post.Status.DRAFT or not obj.published_at or obj.published_at > timezone.now():
            return self.preview_url(obj)
        return obj.get_absolute_url()

    @admin.display(description="Preview")
    def preview_link(self, obj):
        if not obj or not obj.pk:
            return "Save the post to preview it."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Preview saved post</a>',
            self.preview_url(obj),
        )

    @method_decorator(require_safe)
    def preview_data(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not self.has_view_or_change_permission(request, obj):
            return JsonResponse({"detail": "Archives post permission is required."}, status=403)
        if obj is None:
            return JsonResponse({"detail": "This post isn't available."}, status=404)
        data = dict(PostDetailSerializer(obj, context={"request": request}).data)
        data["status"] = obj.status
        data["edit_url"] = request.build_absolute_uri(
            reverse("admin:archives_post_change", args=(obj.pk,))
        )
        response = JsonResponse(data)
        response["Cache-Control"] = "private, no-store, no-cache, max-age=0"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def response_add(self, request, obj, post_url_continue=None):
        if "_preview" in request.POST:
            return HttpResponseRedirect(self.preview_url(obj))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "_preview" in request.POST:
            return HttpResponseRedirect(self.preview_url(obj))
        return super().response_change(request, obj)


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
