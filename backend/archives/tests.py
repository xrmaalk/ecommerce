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


@override_settings(ARCHIVES_FRONTEND_URL="https://organicarchives.organicemperor.com")
class ArchivesPreviewTests(APITestCase):
    def setUp(self):
        self.publisher = get_user_model().objects.create_user(
            username="preview-publisher", password="local-test-password", is_staff=True,
        )
        self.publisher.groups.add(Group.objects.get(name=PUBLISHER_GROUP_NAME))
        self.draft = Post.objects.create(
            title="A private release", slug="private-release", excerpt="Saved draft excerpt",
        )
        self.block = PostBlock.objects.create(post=self.draft, text="**Saved draft** content")
        self.preview_url = reverse("admin:archives_post_preview_data", args=(self.draft.pk,))
        self.frontend_url = f"https://organicarchives.organicemperor.com/preview/{self.draft.pk}"

    def form_data(self):
        return {
            "title": "An updated draft", "slug": self.draft.slug, "kind": "release",
            "excerpt": "Revised introduction", "author_name": "The editors", "status": "draft",
            "blocks-TOTAL_FORMS": "1", "blocks-INITIAL_FORMS": "1",
            "blocks-MIN_NUM_FORMS": "0", "blocks-MAX_NUM_FORMS": "1000",
            "blocks-0-id": str(self.block.pk), "blocks-0-post": str(self.draft.pk),
            "blocks-0-kind": "text", "blocks-0-position": "0", "blocks-0-text": "The revised body.",
            "_preview": "Save and preview",
        }

    def test_preview_requires_active_staff_with_archives_post_permission(self):
        self.assertEqual(self.client.get(self.preview_url).status_code, 302)
        for name, staff, active, permitted, expected in (
            ("reader", False, True, False, 302),
            ("nonstaff-with-permission", False, True, True, 302),
            ("other-staff", True, True, False, 403),
            ("inactive-publisher", True, False, True, 302),
        ):
            with self.subTest(user=name):
                user = get_user_model().objects.create_user(username=name, is_staff=staff, is_active=active)
                if permitted:
                    user.groups.add(Group.objects.get(name=PUBLISHER_GROUP_NAME))
                self.client.force_login(user)
                response = self.client.get(self.preview_url)
                self.assertEqual(response.status_code, expected)
                self.assertNotContains(response, self.draft.title, status_code=expected)
        self.client.force_login(self.publisher)
        self.assertEqual(self.client.get(self.preview_url).status_code, 200)
        self.publisher.groups.clear()
        self.assertEqual(self.client.get(self.preview_url).status_code, 403)

    def test_publisher_preview_is_uncached_and_does_not_publish_or_notify(self):
        reader = get_user_model().objects.create_user(username="preview-subscriber")
        ArchiveSubscription.objects.create(user=reader, last_read_at=timezone.now() - timedelta(days=1))
        self.client.force_login(self.publisher)
        original_updated_at = self.draft.updated_at
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "draft")
        self.assertIsNone(response.json()["published_at"])
        self.assertEqual(response.json()["blocks"][0]["text"], self.block.text)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, "draft")
        self.assertEqual(self.draft.updated_at, original_updated_at)
        self.assertEqual(self.client.get(reverse("archives:post-list")).data["count"], 0)
        self.assertEqual(self.client.get(reverse("archives:post-detail", args=(self.draft.slug,))).status_code, 404)
        self.client.force_login(reader)
        self.assertEqual(self.client.get(reverse("archives:notifications")).data["unread_count"], 0)

    @override_settings(
        CORS_ALLOWED_ORIGINS=["https://organicarchives.organicemperor.com"],
        ALLOWED_HOSTS=["testserver", "api.organicemperor.com", "admin.organicemperor.com"],
    )
    def test_preview_uses_admin_origin_session_and_allows_credentialed_archives_origin(self):
        self.client.force_login(self.publisher)
        for host in ("api.organicemperor.com", "admin.organicemperor.com"):
            with self.subTest(publisher_host=host):
                response = self.client.get(
                    self.preview_url, HTTP_HOST=host,
                    HTTP_ORIGIN="https://organicarchives.organicemperor.com",
                    HTTP_X_FORWARDED_PROTO="https",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Access-Control-Allow-Origin"], "https://organicarchives.organicemperor.com")
                self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
                self.assertEqual(response.json()["edit_url"],
                                 f"https://{host}/admin/archives/post/{self.draft.pk}/change/")
        forbidden_origin = self.client.get(self.preview_url, HTTP_ORIGIN="https://untrusted.example")
        self.assertNotIn("Access-Control-Allow-Origin", forbidden_origin)

    def test_scheduled_posts_can_be_previewed_but_public_and_interaction_routes_stay_private(self):
        self.client.force_login(self.publisher)
        self.draft.status = "published"
        self.draft.published_at = timezone.now() + timedelta(days=1)
        self.draft.save()
        self.assertEqual(self.client.get(self.preview_url).status_code, 200)
        for name in ("post-detail", "post-engagement", "post-like", "post-comment"):
            url = reverse(f"archives:{name}", args=(self.draft.slug,))
            method, data = (self.client.put, {}) if name == "post-like" else (
                (self.client.post, {"body": "Should not be posted"}) if name == "post-comment" else (self.client.get, {})
            )
            with self.subTest(route=name):
                self.assertEqual(method(url, data).status_code, 404)
        self.assertFalse(PostLike.objects.filter(post=self.draft).exists())
        self.assertFalse(PostComment.objects.filter(post=self.draft).exists())

    def test_save_and_preview_validates_and_saves_draft_and_inlines(self):
        self.client.force_login(self.publisher)
        change_url = reverse("admin:archives_post_change", args=(self.draft.pk,))
        page = self.client.get(change_url)
        self.assertContains(page, 'name="_preview"')
        self.assertContains(page, "Preview saved post")
        self.assertContains(page, self.frontend_url)
        response = self.client.post(change_url, self.form_data())
        self.assertRedirects(response, self.frontend_url, fetch_redirect_response=False)
        self.draft.refresh_from_db()
        self.block.refresh_from_db()
        self.assertEqual(self.draft.status, "draft")
        self.assertIsNone(self.draft.published_at)
        self.assertEqual(self.draft.title, "An updated draft")
        self.assertEqual(self.block.text, "The revised body.")
        invalid = self.form_data()
        invalid["blocks-0-text"] = ""
        invalid["title"] = "Must not save"
        response = self.client.post(change_url, invalid)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter the section&#x27;s text.")
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.title, "An updated draft")

    def test_new_draft_can_be_saved_and_previewed(self):
        self.client.force_login(self.publisher)
        data = self.form_data()
        data["slug"] = "new-preview-draft"
        data["blocks-INITIAL_FORMS"] = "0"
        del data["blocks-0-id"]
        del data["blocks-0-post"]
        response = self.client.post(reverse("admin:archives_post_add"), data)
        draft = Post.objects.get(slug="new-preview-draft")
        self.assertRedirects(response, f"https://organicarchives.organicemperor.com/preview/{draft.pk}",
                             fetch_redirect_response=False)
        self.assertEqual(draft.status, "draft")
        self.assertEqual(draft.blocks.get().text, "The revised body.")

    def test_preview_is_read_only_and_unknown_post_returns_not_found(self):
        self.client.force_login(self.publisher)
        self.assertEqual(self.client.get(reverse("admin:archives_post_preview_data", args=(999999,))).status_code, 404)
        for method in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertEqual(method(self.preview_url, {"status": "published"}).status_code, 405)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, "draft")


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
