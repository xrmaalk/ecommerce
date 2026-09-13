from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadView,
    PostCommentView,
    PostDetailView,
    PostEngagementView,
    PostLikeView,
    PostListView,
    SubscriptionView,
)

app_name = "archives"
urlpatterns = [
    path("posts/", PostListView.as_view(), name="post-list"),
    path("posts/<slug:slug>/", PostDetailView.as_view(), name="post-detail"),
    path(
        "posts/<slug:slug>/engagement/",
        PostEngagementView.as_view(),
        name="post-engagement",
    ),
    path(
        "posts/<slug:slug>/like/",
        PostLikeView.as_view(),
        name="post-like",
    ),
    path(
        "posts/<slug:slug>/comments/",
        PostCommentView.as_view(),
        name="post-comment",
    ),
    path("subscription/", SubscriptionView.as_view(), name="subscription"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/read/",
        NotificationReadView.as_view(),
        name="notifications-read",
    ),
]
