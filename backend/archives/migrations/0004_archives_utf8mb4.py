from django.db import migrations


ARCHIVES_TABLES = (
    "archives_postblock",
    "archives_postcomment",
    "archives_post",
)


def convert_archives_to_utf8mb4(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    with schema_editor.connection.cursor() as cursor:
        for table in ARCHIVES_TABLES:
            quoted_table = schema_editor.quote_name(table)
            cursor.execute(
                f"""
                ALTER TABLE {quoted_table}
                CONVERT TO CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("archives", "0003_reader_interactions"),
    ]

    operations = [
        migrations.RunPython(
            convert_archives_to_utf8mb4,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
