import math

from rest_framework import serializers

from .models import Post, PostBlock, PostComment, video_embed_url


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


class PostCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = PostComment
        fields = ("id", "author_name", "body", "created_at", "is_mine")
        read_only_fields = ("id", "author_name", "created_at", "is_mine")

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Write a comment before posting.")
        return value

    def get_author_name(self, obj):
        first_name = obj.user.first_name.strip()
        last_name = obj.user.last_name.strip()
        if first_name and last_name:
            return f"{first_name} {last_name[0]}."
        return first_name or "Reader"

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.pk == obj.user_id
        )
