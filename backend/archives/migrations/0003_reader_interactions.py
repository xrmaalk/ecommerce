import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


PUBLISHER_GROUP_NAME = "Organic Archives Publishers"
PUBLISHER_MODELS = (
    "archivesubscription",
    "post",
    "postblock",
    "postcomment",
    "postlike",
)
PUBLISHER_ACTIONS = ("add", "change", "delete", "view")


def update_publisher_group(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    database = schema_editor.connection.alias
    group, _ = Group.objects.using(database).get_or_create(
        name=PUBLISHER_GROUP_NAME
    )
    permissions = []
    for model_name in PUBLISHER_MODELS:
        model = apps.get_model("archives", model_name)
        content_type, _ = ContentType.objects.using(database).get_or_create(
            app_label="archives",
            model=model_name,
        )
        for action in PUBLISHER_ACTIONS:
            permission, _ = Permission.objects.using(database).get_or_create(
                content_type=content_type,
                codename=f"{action}_{model_name}",
                defaults={"name": f"Can {action} {model._meta.verbose_name}"},
            )
            permissions.append(permission)
    group.permissions.set(permissions)


def restore_publisher_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    database = schema_editor.connection.alias
    group = Group.objects.using(database).filter(
        name=PUBLISHER_GROUP_NAME
    ).first()
    if group is None:
        return
    permissions = Permission.objects.using(database).filter(
        content_type__app_label="archives",
        content_type__model__in=("post", "postblock"),
        codename__in=(
            "add_post",
            "change_post",
            "delete_post",
            "view_post",
            "add_postblock",
            "change_postblock",
            "delete_postblock",
            "view_postblock",
        ),
    )
    group.permissions.set(permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("archives", "0002_create_publisher_group"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchiveSubscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("subscribed_at", models.DateTimeField(auto_now_add=True)),
                ("last_read_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="archive_subscription",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-subscribed_at",)},
        ),
        migrations.CreateModel(
            name="PostComment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("body", models.TextField(max_length=1200)),
                ("is_visible", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="archives.post",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="archive_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("created_at", "id"),
                "indexes": [
                    models.Index(
                        fields=("post", "is_visible", "created_at"),
                        name="archives_comment_public_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="PostLike",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="archives.post",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="archive_likes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("post", "user"),
                        name="unique_archives_post_like",
                    )
                ],
            },
        ),
        migrations.RunPython(update_publisher_group, restore_publisher_group),
    ]
