from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from .seo import product_page, post_page, archives_sitemap, archives_robots
from .share_images import share_image

admin.site.site_header = "OrganicEmperor.com Administration"
admin.site.site_title = "OrganicEmperor.com Admin"
admin.site.index_title = "Store Operations"


def api_root(request):
    return JsonResponse(
        {
            "service": "OrganicEmperor.com Commerce API",
            "status": "online",
            "health": "/health/",
            "catalog": "/api/v1/",
            "authentication": "/api/v1/auth/",
            "commerce": "/api/v1/commerce/",
            "administration": "/admin/",
        }
    )


urlpatterns = [
    path("site/storefront/share-image.png", share_image, {"site": "storefront"}, name="seo-storefront-image"),
    path("site/archives/share-image.png", share_image, {"site": "archives"}, name="seo-archives-image"),
    path("site/storefront/products/<slug:slug>/share-image.png", share_image, {"site": "storefront"}, name="seo-product-image"),
    path("site/archives/posts/<slug:slug>/share-image.png", share_image, {"site": "archives"}, name="seo-post-image"),
    path("site/storefront/products/<slug:slug>", product_page, name="seo-product"),
    path("site/archives/posts/<slug:slug>", post_page, name="seo-post"),
    path("site/archives/sitemap.xml", archives_sitemap, name="seo-archives-sitemap"),
    path("site/archives/robots.txt", archives_robots, name="seo-archives-robots"),
    path("", lambda request: JsonResponse({
        "service": "OrganicEmperor.com Commerce API",
        "status": "online",
    })),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/commerce/", include("commerce.urls")),
    path("api/v1/archives/", include("archives.urls")),
    path("api/v1/", include("catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
else:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
