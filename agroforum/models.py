from django.conf import settings
from django.db import models
from django.urls import reverse
from cloudinary.models import CloudinaryField


class Topic(models.Model):
    """Forum topics/categories"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon class")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Topics"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("agroforum:topic", kwargs={"slug": self.slug})


class Post(models.Model):
    """Forum post - Instagram-like feed item"""
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_posts"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts"
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    image = CloudinaryField('image', folder='agroforum/posts/', blank=True, null=True)

    # Engagement
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="PostLike",
        related_name="liked_forum_posts",
        blank=True
    )

    # Metadata
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["topic", "-created_at"]),
        ]

    def __str__(self):
        return self.title or f"Post by {self.author.username} ({self.created_at:%Y-%m-%d})"

    def get_absolute_url(self):
        return reverse("agroforum:post_detail", kwargs={"pk": self.pk})

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(parent__isnull=True).count()

    @property
    def total_comment_count(self):
        """Count all comments including nested replies"""
        return self.comments.count()

    def user_has_liked(self, user):
        if user.is_authenticated:
            return PostLike.objects.filter(post=self, user=user).exists()
        return False

    @property
    def user_has_liked_current(self):
        """Template-friendly property - requires request context"""
        # This is set by the view when rendering
        return getattr(self, '_user_liked', False)


class PostLike(models.Model):
    """Post likes with timestamp"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["post", "user"]
        ordering = ["-created_at"]


class Comment(models.Model):
    """Nested comments - Facebook-style with unlimited nesting"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forum_comments"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )
    content = models.TextField()
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="CommentLike",
        related_name="liked_forum_comments",
        blank=True
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "parent", "created_at"]),
        ]

    def __str__(self):
        prefix = "Reply" if self.parent else "Comment"
        return f"{prefix} by {self.author.username} on {self.post}"

    @property
    def is_top_level(self):
        return self.parent is None

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def reply_count(self):
        return self.replies.count()

    def user_has_liked(self, user):
        if user.is_authenticated:
            return CommentLike.objects.filter(comment=self, user=user).exists()
        return False

    @property
    def user_has_liked_current(self):
        """Template-friendly property"""
        return getattr(self, '_user_liked', False)

    def get_depth(self):
        """Get nesting depth (0 = top-level)"""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth


class CommentLike(models.Model):
    """Comment likes"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["comment", "user"]
        ordering = ["-created_at"]