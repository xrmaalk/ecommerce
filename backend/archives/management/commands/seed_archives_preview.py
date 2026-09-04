from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from archives.models import Post, PostBlock


class Command(BaseCommand):
    help = "Create sample posts only in the isolated .archives-preview.sqlite3 development database."

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if not settings.DEBUG or db["ENGINE"] != "django.db.backends.sqlite3" or Path(db["NAME"]).name != ".archives-preview.sqlite3":
            raise CommandError(
                "Preview content requires DEBUG=True and the separate .archives-preview.sqlite3 database.")
        samples = [
            ("Welcome to the OrganicArchives", "update", "From the editors",
             "A new home for our articles, announcements, and the stories behind OrganicEmperor."),
            ("The small rituals that make a day feel different", "article", "Everyday rituals",
             "A warm cup of tea. A few unhurried minutes. A closer look at the routines we make our own."),
            ("Reading the label: a place to start", "article", "Ingredients",
             "Good questions begin with curiosity. Notes on getting to know the ingredients in your everyday routine."),
            ("A new chapter for OrganicEmperor online", "release", "Company news",
             "Introducing a dedicated space for the news and announcements we want to share with you."),
            ("Behind the scenes, one detail at a time", "update", "Behind the scenes",
             "A notebook for the work in progress, the questions we’re asking, and what comes next."),
            ("Making room for a slower morning", "article", "Everyday rituals",
             "An invitation to pause, put the kettle on, and find a little space before the day begins."),
        ]
        from django.utils.text import slugify
        for index, (title, kind, topic, excerpt) in enumerate(samples):
            post, created = Post.objects.get_or_create(slug=slugify(title), defaults={
                "title": title, "kind": kind, "topic": topic, "excerpt": excerpt,
                "status": "published", "published_at": timezone.now() - timedelta(days=index),
            })
            if created:
                PostBlock.objects.create(
                    post=post, position=0, text="This is sample editorial content for the local OrganicArchives preview. It demonstrates how a published post will appear; it is not a live announcement.")
                PostBlock.objects.create(
                    post=post, position=1, kind="heading", text="A space for the story")
                PostBlock.objects.create(post=post, position=2, text=excerpt +
                                         "\n\nThe archives bring articles, news releases, and shorter updates together in one place. Each post can include photographs, video, and notes from the people behind the work.")
                PostBlock.objects.create(post=post, position=3, kind="quote",
                                         text="Ideas. Ingredients. Everyday rituals.", caption="OrganicArchives")
        self.stdout.write(self.style.SUCCESS(
            "Local preview posts are ready. No production content was changed."))
