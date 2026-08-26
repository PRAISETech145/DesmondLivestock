from django.core.management.base import BaseCommand
from listings.models import Category


class Command(BaseCommand):
    help = "Check categories"

    def handle(self, *args, **options):
        for c in Category.objects.all():
            self.stdout.write(f"Name: '{c.name}', Slug: '{c.slug}'")