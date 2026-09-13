from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from archives.publisher import (
    PUBLISHER_GROUP_NAME,
    PUBLISHER_PERMISSION_CODENAMES,
)


class Command(BaseCommand):
    help = (
        "Make an existing user an Organic Archives publisher. The user is made "
        "active and staff, removed from every other group and direct permission, "
        "and denied superuser status."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username of an existing account")

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        try:
            user = user_model._default_manager.get(
                **{username_field: options["username"]}
            )
        except user_model.DoesNotExist as exc:
            raise CommandError(
                f"No user with {username_field} {options['username']!r} exists."
            ) from exc

        try:
            publisher_group = Group.objects.get(name=PUBLISHER_GROUP_NAME)
        except Group.DoesNotExist as exc:
            raise CommandError(
                "The publisher group is missing. Run `python manage.py migrate` first."
            ) from exc

        publisher_permissions = Permission.objects.filter(
            content_type__app_label="archives",
            codename__in=PUBLISHER_PERMISSION_CODENAMES,
        )
        if set(publisher_permissions.values_list("codename", flat=True)) != set(
            PUBLISHER_PERMISSION_CODENAMES
        ):
            raise CommandError(
                "The publisher permissions are incomplete. Run `python manage.py migrate` "
                "first."
            )
        publisher_group.permissions.set(publisher_permissions)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = False
        user.save(update_fields=("is_active", "is_staff", "is_superuser"))
        user.groups.set((publisher_group,))
        user.user_permissions.clear()

        self.stdout.write(
            self.style.SUCCESS(
                f"{options['username']} can now administer Organic Archives only."
            )
        )
