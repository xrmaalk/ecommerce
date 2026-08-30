from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as serve_media

admin.site.site_header = "Organic Emperor Administration"
admin.site.site_title = "Organic Emperor Admin"
admin.site.index_title = "Store Operations"


def api_root(request):
    return JsonResponse(
        {
            "service": "Organic Emperor Commerce API",
            "status": "online",
            "health": "/health/",
            "catalog": "/api/v1/",
            "authentication": "/api/v1/auth/",
            "commerce": "/api/v1/commerce/",
            "administration": "/admin/",
        }
    )


urlpatterns = [
    path("", lambda request: JsonResponse({
        "service": "Organic Emperor Commerce API",
        "status": "online",
    })),
    path("health/", lambda request: JsonResponse({"status": "ok"})),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/commerce/", include("commerce.urls")),
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
