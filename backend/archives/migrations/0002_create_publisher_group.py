from django.db import migrations


PUBLISHER_GROUP_NAME = "Organic Archives Publishers"
PUBLISHER_MODELS = ("post", "postblock")
PUBLISHER_ACTIONS = ("add", "change", "delete", "view")


def create_publisher_group(apps, schema_editor):
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


def remove_publisher_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.using(schema_editor.connection.alias).filter(
        name=PUBLISHER_GROUP_NAME
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archives", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_publisher_group, remove_publisher_group),
    ]
