import tempfile
from datetime import timedelta
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import (
    ArchiveSubscription,
    Post,
    PostBlock,
    PostComment,
    PostLike,
    video_embed_url,
)
from .publisher import PUBLISHER_GROUP_NAME, PUBLISHER_PERMISSION_CODENAMES


class ArchivesTests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.public = Post.objects.create(title="From the editors", slug="from-the-editors", excerpt="The journal begins.", kind="update", status="published", published_at=self.now - timedelta(days=1))
        self.draft = Post.objects.create(title="Unannounced", slug="unannounced", excerpt="Private draft", published_at=self.now - timedelta(days=2))
        self.future = Post.objects.create(title="Tomorrow", slug="tomorrow", excerpt="Scheduled", status="published", published_at=self.now + timedelta(days=1))
        self.list_url = reverse("archives:post-list")

    def detail_url(self, post):
        return reverse("archives:post-detail", kwargs={"slug": post.slug})

    def test_public_list_and_detail_exclude_drafts_future_and_undated_posts(self):
        undated = Post.objects.create(title="No date", slug="no-date", status="published")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["slug"] for p in response.data["results"]], [self.public.slug])
        self.assertEqual(self.client.get(self.detail_url(self.public)).status_code, 200)
        for private in (self.draft, self.future, undated):
            self.assertEqual(self.client.get(self.detail_url(private)).status_code, 404)
        self.assertEqual(self.client.get(self.list_url, {"search": "Private draft"}).data["count"], 0)

    def test_search_body_and_filter_kind_without_duplicate_results(self):
        PostBlock.objects.create(post=self.public, text="Botanical notebook", position=1)
        PostBlock.objects.create(post=self.public, text="Botanical notes", position=2)
        response = self.client.get(self.list_url, {"search": "Botanical", "kind": "update"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get(self.list_url, {"kind": "article"}).data["count"], 0)

    def test_pagination_and_stable_newest_first_order(self):
        for index in range(17):
            Post.objects.create(title=f"Post {index}", slug=f"post-{index}", status="published", published_at=self.now)
        first = self.client.get(self.list_url).data
        second = self.client.get(self.list_url, {"page": 2}).data
        self.assertEqual(first["count"], 18)
        self.assertEqual(len(first["results"]), 15)
        self.assertEqual(len(second["results"]), 3)
        self.assertEqual(first["results"][0]["slug"], "post-16")
        self.assertEqual(second["results"][-1]["slug"], self.public.slug)
        self.assertTrue(first["next"])
        self.assertIsNone(second["next"])

    def test_public_api_is_read_only_even_for_authenticated_users(self):
        for authenticated in (False, True):
            if authenticated:
                user = get_user_model().objects.create_user(username="reader", password="local-test-password")
                self.client.force_authenticate(user=user)
            self.assertEqual(self.client.post(self.list_url, {"title": "Unauthorized"}).status_code, 405)
            self.assertEqual(self.client.patch(self.detail_url(self.public), {"title": "Unauthorized"}).status_code, 405)
            self.assertEqual(self.client.delete(self.detail_url(self.public)).status_code, 405)

    def test_reader_can_like_public_posts_without_editorial_access(self):
        reader = get_user_model().objects.create_user(
            username="reader@example.com",
            password="local-test-password",
        )
        like_url = reverse("archives:post-like", kwargs={"slug": self.public.slug})
        engagement_url = reverse(
            "archives:post-engagement",
            kwargs={"slug": self.public.slug},
        )

        self.assertEqual(self.client.put(like_url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_login(reader)
        self.assertEqual(self.client.put(like_url).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.put(like_url).status_code, status.HTTP_200_OK)
        self.assertEqual(PostLike.objects.filter(post=self.public).count(), 1)
        engagement = self.client.get(engagement_url).data
        self.assertTrue(engagement["liked"])
        self.assertEqual(engagement["like_count"], 1)

        self.assertEqual(self.client.delete(like_url).status_code, status.HTTP_200_OK)
        self.assertFalse(self.client.get(engagement_url).data["liked"])
        self.assertEqual(
            self.client.put(
                reverse("archives:post-like", kwargs={"slug": self.draft.slug})
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertFalse(reader.is_staff)
        self.assertEqual(
            self.client.get(reverse("admin:archives_post_changelist")).status_code,
            status.HTTP_302_FOUND,
        )

    def test_reader_comments_are_public_and_can_be_moderated(self):
        reader = get_user_model().objects.create_user(
            username="commenter@example.com",
            first_name="Avery",
            last_name="Stone",
            password="local-test-password",
        )
        comment_url = reverse(
            "archives:post-comment",
            kwargs={"slug": self.public.slug},
        )
        engagement_url = reverse(
            "archives:post-engagement",
            kwargs={"slug": self.public.slug},
        )

        self.assertEqual(
            self.client.post(comment_url, {"body": "Hello"}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_login(reader)
        response = self.client.post(
            comment_url,
            {"body": "  Thoughtful and useful.  "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author_name"], "Avery S.")
        self.assertEqual(response.data["body"], "Thoughtful and useful.")
        self.assertTrue(response.data["is_mine"])

        comment = PostComment.objects.get()
        comment.is_visible = False
        comment.save(update_fields=("is_visible",))
        engagement = self.client.get(engagement_url).data
        self.assertEqual(engagement["comment_count"], 0)
        self.assertEqual(engagement["comments"], [])
        self.assertEqual(
            self.client.post(comment_url, {"body": "   "}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_subscription_surfaces_only_newly_published_notifications(self):
        reader = get_user_model().objects.create_user(
            username="subscriber@example.com",
            password="local-test-password",
        )
        self.client.force_login(reader)
        subscription_url = reverse("archives:subscription")
        notifications_url = reverse("archives:notifications")

        subscribed = self.client.put(subscription_url)
        self.assertEqual(subscribed.status_code, status.HTTP_201_CREATED)
        self.assertTrue(subscribed.data["subscribed"])
        self.assertEqual(self.client.get(notifications_url).data["unread_count"], 0)

        subscription = ArchiveSubscription.objects.get(user=reader)
        published_at = timezone.now()
        subscription.last_read_at = published_at - timedelta(seconds=1)
        subscription.save(update_fields=("last_read_at",))
        Post.objects.create(
            title="New for subscribers",
            slug="new-for-subscribers",
            excerpt="A new notification.",
            status="published",
            published_at=published_at,
        )
        notifications = self.client.get(notifications_url).data
        self.assertTrue(notifications["subscribed"])
        self.assertEqual(notifications["unread_count"], 1)
        self.assertEqual(notifications["results"][0]["slug"], "new-for-subscribers")

        marked_read = self.client.post(reverse("archives:notifications-read"))
        self.assertEqual(marked_read.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(notifications_url).data["unread_count"], 0)
        self.assertEqual(self.client.delete(subscription_url).status_code, status.HTTP_200_OK)
        self.assertFalse(self.client.get(notifications_url).data["subscribed"])

    def test_reader_interactions_require_csrf(self):
        reader = get_user_model().objects.create_user(
            username="csrf-reader@example.com",
            password="local-test-password",
        )
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(reader)
        like_url = reverse("archives:post-like", kwargs={"slug": self.public.slug})
        self.assertEqual(client.put(like_url).status_code, status.HTTP_403_FORBIDDEN)
        csrf_token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(
            client.put(like_url, HTTP_X_CSRFTOKEN=csrf_token).status_code,
            status.HTTP_201_CREATED,
        )

    def test_admin_publishing_requires_staff_permission(self):
        url = reverse("admin:archives_post_add")
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user(username="customer", password="local-test-password")
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 302)
        user.is_staff = True
        user.save()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_login_and_publisher_pages_render(self):
        response = self.client.get(reverse("admin:archives_post_changelist"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/login.html")
        editor = get_user_model().objects.create_superuser(username="page-editor", password="local-test-password")
        self.client.force_login(editor)
        for name in ("admin:archives_post_changelist", "admin:archives_post_add"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_archives_publisher_is_staff_with_only_archives_access(self):
        publisher = get_user_model().objects.create_user(
            username="publisher",
            password="local-test-password",
            is_active=False,
            is_superuser=True,
        )
        unrelated_group = Group.objects.create(name="Store staff")
        unrelated_permission = Permission.objects.get(
            content_type__app_label="catalog",
            codename="change_product",
        )
        unrelated_group.permissions.add(unrelated_permission)
        publisher.groups.add(unrelated_group)
        publisher.user_permissions.add(unrelated_permission)
        Group.objects.get(name=PUBLISHER_GROUP_NAME).permissions.add(
            unrelated_permission
        )

        call_command("assign_archives_publisher", publisher.username)
        publisher.refresh_from_db()

        self.assertTrue(publisher.is_active)
        self.assertTrue(publisher.is_staff)
        self.assertFalse(publisher.is_superuser)
        self.assertEqual(
            set(publisher.groups.values_list("name", flat=True)),
            {PUBLISHER_GROUP_NAME},
        )
        self.assertFalse(publisher.user_permissions.exists())
        self.assertEqual(
            {
                permission.split(".", 1)[1]
                for permission in publisher.get_all_permissions()
            },
            PUBLISHER_PERMISSION_CODENAMES,
        )

        archive_url = reverse("admin:archives_post_changelist")
        login = self.client.post(
            reverse("admin:login"),
            {
                "username": publisher.username,
                "password": "local-test-password",
                "next": archive_url,
            },
        )
        self.assertRedirects(login, archive_url, fetch_redirect_response=False)
        for name in (
            "admin:index",
            "admin:archives_post_changelist",
            "admin:archives_post_add",
            "admin:archives_postcomment_changelist",
            "admin:archives_postlike_changelist",
            "admin:archives_archivesubscription_changelist",
        ):
            with self.subTest(allowed=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

        for name in (
            "admin:catalog_product_changelist",
            "admin:commerce_order_changelist",
            "admin:auth_user_changelist",
        ):
            with self.subTest(forbidden=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

        index = self.client.get(reverse("admin:index"))
        self.assertContains(index, "OrganicArchives")
        self.assertNotContains(index, "Products")
        self.assertNotContains(index, "Orders")

    def test_publication_and_accessible_image_validation(self):
        self.public.published_at = None
        with self.assertRaises(ValidationError):
            self.public.full_clean()
        with self.assertRaises(ValidationError):
            PostBlock(post=self.public, kind="image", image="photo.png").full_clean()
        with self.assertRaises(ValidationError):
            PostBlock(post=self.public, kind="text", text="  ").full_clean()

    def test_publisher_can_publish_a_post_with_image_and_video_inlines(self):
        publisher = get_user_model().objects.create_user(
            username="post-publisher",
            password="local-test-password",
        )
        call_command("assign_archives_publisher", publisher.username)
        self.client.force_login(publisher)
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            buffer = BytesIO()
            Image.new("RGB", (2, 2), "green").save(buffer, format="PNG")
            data = {
                "title": "An editor's post", "slug": "editor-post", "kind": "article",
                "excerpt": "Uploaded through the real publishing form.", "author_name": "The editors",
                "status": "published", "published_at_0": "2020-01-01", "published_at_1": "12:00:00",
                "blocks-TOTAL_FORMS": "3", "blocks-INITIAL_FORMS": "0",
                "blocks-MIN_NUM_FORMS": "0", "blocks-MAX_NUM_FORMS": "1000",
                "blocks-0-kind": "text", "blocks-0-position": "0", "blocks-0-text": "The story starts here.",
                "blocks-1-kind": "image", "blocks-1-position": "1", "blocks-1-alt_text": "Green sample image",
                "blocks-1-image": SimpleUploadedFile("inline.png", buffer.getvalue(), content_type="image/png"),
                "blocks-2-kind": "video", "blocks-2-position": "2",
                "blocks-2-video": SimpleUploadedFile("inline.mp4", b"sample-video", content_type="video/mp4"),
                "_save": "Save",
            }
            response = self.client.post(reverse("admin:archives_post_add"), data, format="multipart")
            self.assertEqual(response.status_code, 302)
            post = Post.objects.get(slug="editor-post")
            self.assertEqual(post.blocks.count(), 3)
            self.client.logout()
            published = self.client.get(self.detail_url(post))
            self.assertEqual(published.status_code, 200)
            self.assertEqual([block["kind"] for block in published.data["blocks"]], ["text", "image", "video"])

    def test_embed_urls_are_restricted_to_canonical_players(self):
        valid = {
            "https://www.youtube.com/watch?v=aqz-KE-bpKQ": "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ",
            "https://youtu.be/aqz-KE-bpKQ": "https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ",
            "https://vimeo.com/123456": "https://player.vimeo.com/video/123456",
        }
        for value, expected in valid.items():
            block = PostBlock(post=self.public, kind="embed", video_url=value)
            block.full_clean()
            self.assertEqual(video_embed_url(value), expected)
        for value in ("javascript:alert(1)", "https://youtube.com.evil.test/watch?v=aqz-KE-bpKQ", "http://youtu.be/aqz-KE-bpKQ", "https://youtu.be:444/aqz-KE-bpKQ", "https://youtu.be:nope/aqz-KE-bpKQ", "https://example.com/video", "https://youtube.com/watch?v=invalid"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                PostBlock(post=self.public, kind="embed", video_url=value).full_clean()

    def test_video_file_type_and_size_validation(self):
        invalid = SimpleUploadedFile("bad.html", b"<script>alert(1)</script>", content_type="text/html")
        with self.assertRaises(ValidationError):
            PostBlock(post=self.public, kind="video", video=invalid).full_clean()
        oversized = SimpleUploadedFile("big.mp4", b"video", content_type="video/mp4")
        oversized.size = 101 * 1024 * 1024
        with self.assertRaises(ValidationError):
            PostBlock(post=self.public, kind="video", video=oversized).full_clean()

    def test_media_serialization_order_and_reading_time(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            buffer = BytesIO()
            Image.new("RGB", (2, 2), "green").save(buffer, format="PNG")
            photo = SimpleUploadedFile("photo.png", buffer.getvalue(), content_type="image/png")
            PostBlock.objects.create(post=self.public, position=3, kind="image", image=photo, alt_text="Green sample")
            PostBlock.objects.create(post=self.public, position=1, kind="text", text="word " * 440)
            PostBlock.objects.create(post=self.public, position=2, kind="embed", video_url="https://youtu.be/aqz-KE-bpKQ")
            video = SimpleUploadedFile("clip.mp4", b"sample-video", content_type="video/mp4")
            PostBlock.objects.create(post=self.public, position=4, kind="video", video=video)
            response = self.client.get(self.detail_url(self.public))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["reading_minutes"], 2)
            self.assertTrue(response.data["has_video"])
            blocks = response.data["blocks"]
            self.assertEqual([b["kind"] for b in blocks], ["text", "embed", "image", "video"])
            self.assertTrue(blocks[2]["image"].startswith("http://testserver/media/archives/images/"))
            self.assertEqual(blocks[2]["alt_text"], "Green sample")
            self.assertTrue(blocks[3]["video"].endswith(".mp4"))
