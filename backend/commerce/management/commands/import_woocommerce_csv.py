import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Category, Product, ProductImage
from commerce.models import ImportJob


def cell(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def truthy(value):
    return str(value).strip().lower() in {"1", "yes", "true", "published", "visible"}


def decimal_value(value, default="0.00"):
    try:
        return Decimal(str(value or default)).quantize(Decimal("0.01"))
    except InvalidOperation as error:
        raise ValueError(f"Invalid price: {value}") from error


class Command(BaseCommand):
    help = "Idempotently import products from a standard WooCommerce product CSV export."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without saving database changes.")
        parser.add_argument(
            "--image-base-dir",
            type=Path,
            help="Optional local directory containing image files referenced by the WooCommerce Images column.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"].expanduser().resolve()
        image_base_dir = options.get("image_base_dir")
        if not csv_path.is_file():
            raise CommandError(f"CSV file not found: {csv_path}")
        if image_base_dir:
            image_base_dir = image_base_dir.expanduser().resolve()
            if not image_base_dir.is_dir():
                raise CommandError(f"Image directory not found: {image_base_dir}")

        counters = {"created": 0, "updated": 0, "skipped": 0, "errors": 0, "images": 0}
        error_rows = []
        with transaction.atomic():
            job = ImportJob.objects.create(source_name=csv_path.name)
            with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                if not reader.fieldnames:
                    raise CommandError("The CSV has no header row.")
                for row_number, row in enumerate(reader, start=2):
                    try:
                        outcome, images = self.import_row(row, image_base_dir, options["dry_run"])
                        counters[outcome] += 1
                        counters["images"] += images
                    except Exception as error:
                        counters["errors"] += 1
                        error_rows.append({"row": row_number, "error": str(error)[:300]})
                        self.stderr.write(self.style.ERROR(f"Row {row_number}: {error}"))

            job.status = ImportJob.Status.COMPLETED if not counters["errors"] else ImportJob.Status.FAILED
            job.created_count = counters["created"]
            job.updated_count = counters["updated"]
            job.skipped_count = counters["skipped"]
            job.error_count = counters["errors"]
            job.summary = {**counters, "error_rows": error_rows[:100], "dry_run": options["dry_run"]}
            job.finished_at = timezone.now()
            job.save()
            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = ", ".join(f"{key}={value}" for key, value in counters.items())
        prefix = "Dry run complete" if options["dry_run"] else "Import complete"
        self.stdout.write(self.style.SUCCESS(f"{prefix}: {summary}"))
        if counters["errors"]:
            raise CommandError(f"Import completed with {counters['errors']} invalid row(s).")

    def import_row(self, row, image_base_dir, dry_run):
        sku = cell(row, "SKU", "Sku", "sku")
        name = cell(row, "Name", "name")
        if not sku or not name:
            raise ValueError("SKU and Name are required.")

        category_value = cell(row, "Categories", "Category", "categories") or "Uncategorized"
        category_name = category_value.split(",")[0].split(">")[-1].strip() or "Uncategorized"
        category, _ = Category.objects.get_or_create(
            slug=slugify(category_name)[:140] or "uncategorized",
            defaults={"name": category_name[:120]},
        )

        regular_price = decimal_value(cell(row, "Regular price", "Regular Price", "regular_price"))
        sale_raw = cell(row, "Sale price", "Sale Price", "sale_price")
        sale_price = decimal_value(sale_raw) if sale_raw else None
        price = sale_price if sale_price is not None else regular_price
        compare_at = regular_price if sale_price is not None and regular_price > sale_price else None
        stock_raw = cell(row, "Stock", "Stock quantity", "stock_quantity")
        in_stock = truthy(cell(row, "In stock?", "In stock", "in_stock"))
        track_inventory = stock_raw != ""
        try:
            inventory = max(0, int(Decimal(stock_raw))) if track_inventory else (0 if not in_stock else 0)
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"Invalid stock quantity: {stock_raw}") from error
        if not track_inventory and not in_stock:
            track_inventory = True

        slug = cell(row, "Slug", "slug") or slugify(name)
        defaults = {
            "name": name[:180],
            "slug": slug[:200],
            "category": category,
            "short_description": cell(row, "Short description", "Short Description")[:280],
            "description": cell(row, "Description", "description"),
            "price_cad": price,
            "compare_at_price_cad": compare_at,
            "inventory_quantity": inventory,
            "track_inventory": track_inventory,
            "is_active": truthy(cell(row, "Published", "published") or "1"),
            "is_featured": truthy(cell(row, "Is featured?", "Featured", "featured")),
        }
        product, created = Product.objects.update_or_create(sku=sku[:80], defaults=defaults)
        image_count = 0
        images_value = cell(row, "Images", "images")
        if image_base_dir and images_value and not dry_run and not product.images.exists():
            for sort_order, reference in enumerate(images_value.split(",")):
                filename = Path(unquote(urlparse(reference.strip()).path)).name
                source_path = (image_base_dir / filename).resolve()
                if source_path.parent != image_base_dir or not source_path.is_file():
                    continue
                with source_path.open("rb") as image_file:
                    image = ProductImage(product=product, alt_text=product.name, sort_order=sort_order)
                    image.image.save(filename, File(image_file), save=True)
                    image_count += 1
        return ("created" if created else "updated"), image_count

