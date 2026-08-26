import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'livestock_marketplace.settings')
import django
django.setup()
from listings.models import Category
for c in Category.objects.all():
    print(f"Name: {c.name}, Slug: {c.slug}")