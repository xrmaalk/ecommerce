from django.db.models import Q
from rest_framework import generics
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)

class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")
        featured = self.request.query_params.get("featured")
        if category: queryset = queryset.filter(category__slug=category)
        if search: queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(sku__icontains=search))
        if featured == "true": queryset = queryset.filter(is_featured=True)
        return queryset

class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    lookup_field = "slug"
    queryset = Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")
