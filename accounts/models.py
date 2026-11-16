from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField


def user_avatar_path(instance, filename):
    """Upload avatars to media/avatars/user_<id>/<filename> (legacy for migration)"""
    ext = filename.split(".")[-1]
    return f"avatars/user_{instance.pk}/avatar.{ext}"

class CustomUser(AbstractUser):
    """
    is_seller controls who can post livestock.
    It is NOT self-service — only the site owner toggles this
    in the Django admin for their own account (and any staff
    they trust). Regular buyers never see a "become a seller" option.
    """
    email = models.EmailField(unique=True)
    is_seller = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)
    avatar = CloudinaryField('image', folder='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=120, blank=True)

    # Verification fields
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, max_length=500, help_text="Admin notes about verification")

    # Email verification (6-digit code system)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    # 6-digit code verification
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_verification_code_sent_at = models.DateTimeField(null=True, blank=True)
    email_verification_code_attempts = models.IntegerField(default=0)

    def __str__(self):
        return self.username

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None

    @property
    def initials(self):
        """Return first letter of username or first name"""
        if self.first_name:
            return self.first_name[0].upper()
        return self.username[0].upper()

    def verify(self, notes=""):
        """Mark user as verified"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.verification_notes = notes
        self.save(update_fields=["is_verified", "verified_at", "verification_notes"])

    def unverify(self):
        """Remove verification"""
        self.is_verified = False
        self.verified_at = None
        self.verification_notes = ""
        self.save(update_fields=["is_verified", "verified_at", "verification_notes"])