from django.shortcuts import render
from listings.models import Livestock, Category
from agroforum.models import Post


def home(request):
    featured = Livestock.objects.filter(status="available").select_related("category")[:6]
    categories = Category.objects.all()
    latest_forum_posts = Post.objects.select_related("author", "topic").prefetch_related("likes")[:3]
    return render(request, "core/home.html", {
        "featured": featured,
        "categories": categories,
        "latest_forum_posts": latest_forum_posts,
    })
