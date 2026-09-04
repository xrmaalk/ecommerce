from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from .models import Post
from .serializers import PostDetailSerializer, PostListSerializer


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
