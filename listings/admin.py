from django.contrib import admin
from .models import Category, Livestock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")


@admin.register(Livestock)
class LivestockAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "status", "posted_by", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "location")
