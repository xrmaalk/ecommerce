from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import ArchiveSubscription, Post, PostComment, PostLike
from .serializers import (
    PostCommentSerializer,
    PostDetailSerializer,
    PostListSerializer,
)


class ArchivesPagination(PageNumberPagination):
    page_size = 15


class PostListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PostListSerializer
    pagination_class = ArchivesPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "excerpt", "topic", "blocks__text"]

    def get_queryset(self):
        posts = Post.objects.public().prefetch_related("blocks")
        if kind := self.request.query_params.get("kind"):
            posts = posts.filter(kind=kind)
        return posts


class PostDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PostDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Post.objects.public().prefetch_related("blocks")


def public_post(slug):
    return get_object_or_404(Post.objects.public(), slug=slug)


class PostEngagementView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        post = public_post(slug)
        comments = post.comments.filter(is_visible=True).select_related("user")
        liked = False
        if request.user.is_authenticated:
            liked = post.likes.filter(user=request.user).exists()
        return Response(
            {
                "like_count": post.likes.count(),
                "liked": liked,
                "comment_count": comments.count(),
                "comments": PostCommentSerializer(
                    comments,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "archives_interaction"

    def put(self, request, slug):
        post = public_post(slug)
        _, created = PostLike.objects.get_or_create(post=post, user=request.user)
        return Response(
            {"liked": True, "like_count": post.likes.count()},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, slug):
        post = public_post(slug)
        PostLike.objects.filter(post=post, user=request.user).delete()
        return Response({"liked": False, "like_count": post.likes.count()})


class PostCommentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "archives_interaction"

    def post(self, request, slug):
        post = public_post(slug)
        serializer = PostCommentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(post=post, user=request.user)
        return Response(
            PostCommentSerializer(
                comment,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "archives_interaction"

    def get(self, request):
        subscription = ArchiveSubscription.objects.filter(user=request.user).first()
        return Response(
            {
                "subscribed": bool(subscription and subscription.is_active),
                "subscribed_at": (
                    subscription.subscribed_at if subscription else None
                ),
            }
        )

    def put(self, request):
        now = timezone.now()
        subscription, created = ArchiveSubscription.objects.get_or_create(
            user=request.user,
            defaults={"is_active": True, "last_read_at": now},
        )
        if not created and not subscription.is_active:
            subscription.is_active = True
            subscription.last_read_at = now
            subscription.save(
                update_fields=("is_active", "last_read_at", "updated_at")
            )
        return Response(
            {
                "subscribed": True,
                "subscribed_at": subscription.subscribed_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        ArchiveSubscription.objects.filter(user=request.user).update(
            is_active=False,
            last_read_at=timezone.now(),
            updated_at=timezone.now(),
        )
        return Response({"subscribed": False, "subscribed_at": None})


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = ArchiveSubscription.objects.filter(
            user=request.user,
            is_active=True,
        ).first()
        if subscription is None:
            return Response(
                {"subscribed": False, "unread_count": 0, "results": []}
            )

        posts = Post.objects.public().filter(
            published_at__gt=subscription.last_read_at
        ).prefetch_related("blocks")
        unread_count = posts.count()
        return Response(
            {
                "subscribed": True,
                "unread_count": unread_count,
                "results": PostListSerializer(
                    posts[:20],
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "archives_interaction"

    def post(self, request):
        ArchiveSubscription.objects.filter(
            user=request.user,
            is_active=True,
        ).update(last_read_at=timezone.now(), updated_at=timezone.now())
        return Response({"unread_count": 0, "results": []})
