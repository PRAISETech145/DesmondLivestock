from django.db import models
from django.conf import settings


class Follow(models.Model):
    """
    Model representing a follow relationship between users.
    follower -> follows -> followed
    """
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
        help_text="The user who is following"
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
        help_text="The user being followed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "followed")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["follower", "followed"]),
            models.Index(fields=["followed", "created_at"]),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.followed}"

    def save(self, *args, **kwargs):
        if self.follower == self.followed:
            raise ValueError("Users cannot follow themselves")
        super().save(*args, **kwargs)