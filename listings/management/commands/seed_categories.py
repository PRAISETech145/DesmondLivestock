from django.core.management.base import BaseCommand
from listings.models import Category


class Command(BaseCommand):
    help = "Seed default categories"

    def handle(self, *args, **options):
        categories = [
            ("Cattle", "cattle"),
            ("Goats", "goats"),
            ("Poultry", "poultry"),
            ("Plant", "plant"),
            ("Animal", "animal"),
            ("Feed Formula", "feed-formula"),
        ]

        created_count = 0
        for name, slug in categories:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": name}
            )
            if created:
                self.stdout.write(f"Created: {cat.name} ({cat.slug})")
                created_count += 1
            else:
                self.stdout.write(f"Exists: {cat.name} ({cat.slug})")

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created_count} new categories."))