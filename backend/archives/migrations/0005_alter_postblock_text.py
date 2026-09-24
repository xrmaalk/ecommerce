from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("archives", "0004_archives_utf8mb4"),
    ]

    operations = [
        migrations.AlterField(
            model_name="postblock",
            name="text",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Text sections support Markdown for links, emphasis, lists, "
                    "headings, quotes, and code. Raw HTML is shown as text and "
                    "scripts never run. Heading and quote sections remain plain text."
                ),
            ),
        ),
    ]
