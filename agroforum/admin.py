from django.contrib import admin
from .models import Topic, Post, Comment


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("order",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "topic", "like_count", "comment_count", "is_pinned", "created_at")
    list_filter = ("topic", "is_pinned", "is_closed", "created_at")
    search_fields = ("title", "content", "author__username")
    readonly_fields = ("like_count", "comment_count", "view_count", "created_at", "updated_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "post", "author", "parent", "like_count", "is_deleted", "created_at")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("content", "author__username", "post__title")
    readonly_fields = ("like_count", "reply_count", "created_at", "updated_at")