from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Livestock(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
    ]

    title = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="livestock")
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    breed = models.CharField(max_length=80, blank=True)
    age = models.CharField(max_length=40, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=120)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="available")
    whatsapp_number = models.CharField(
        max_length=20,
        help_text="Digits only with country code, e.g. 237670000000",
    )
    # Image fields - image_1 is required (enforced at form level), image_2 and image_3 optional
    # Allow null/blank at DB level to support existing records and migration
    image_1 = models.ImageField(upload_to="livestock/%Y/%m/", blank=True, null=True)
    image_2 = models.ImageField(upload_to="livestock/%Y/%m/", blank=True, null=True)
    image_3 = models.ImageField(upload_to="livestock/%Y/%m/", blank=True, null=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Livestock"

    def __str__(self):
        return self.title

    @property
    def whatsapp_link(self):
        import urllib.parse
        message = f"Hi, I'm interested in {self.title} (ref #{self.pk})"
        return f"https://wa.me/{self.whatsapp_number}?text={urllib.parse.quote(message)}"

    @property
    def images_list(self):
        """Return list of all non-empty images for template iteration"""
        imgs = []
        if self.image_1:
            imgs.append(self.image_1)
        if self.image_2:
            imgs.append(self.image_2)
        if self.image_3:
            imgs.append(self.image_3)
        return imgs

    @property
    def first_image(self):
        """Return first image for backward compat with templates"""
        if self.image_1:
            return self.image_1
        if self.image_2:
            return self.image_2
        if self.image_3:
            return self.image_3
        return None
