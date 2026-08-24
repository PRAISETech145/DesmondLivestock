from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Marketplace Role", {"fields": ("is_seller", "phone")}),
        ("Verification", {"fields": ("is_verified", "verified_at", "verification_notes")}),
    )
    list_display = ("username", "email", "is_seller", "is_verified", "is_staff")
    list_filter = UserAdmin.list_filter + ("is_seller", "is_verified")
    readonly_fields = ("verified_at",)


admin.site.register(CustomUser, CustomUserAdmin)
