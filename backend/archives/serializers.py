import math

from rest_framework import serializers

from .models import Post, PostBlock, video_embed_url


class PostBlockSerializer(serializers.ModelSerializer):
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = PostBlock
        fields = ("id", "kind", "text", "image", "alt_text", "video", "embed_url", "caption")

    def get_embed_url(self, obj):
        try:
            return video_embed_url(obj.video_url) if obj.kind == "embed" else ""
        except ValueError:
            return ""


class PostListSerializer(serializers.ModelSerializer):
    reading_minutes = serializers.SerializerMethodField()
    has_video = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ("id", "title", "slug", "kind", "topic", "excerpt", "author_name", "cover_image",
                  "cover_alt", "published_at", "reading_minutes", "has_video")

    def get_reading_minutes(self, obj):
        return max(1, math.ceil(sum(len(block.text.split()) for block in obj.blocks.all()) / 220))

    def get_has_video(self, obj):
        return any(block.kind in ("video", "embed") for block in obj.blocks.all())


class PostDetailSerializer(PostListSerializer):
    blocks = PostBlockSerializer(many=True, read_only=True)

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ("blocks", "updated_at")
