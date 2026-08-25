from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Comment, CommentLike, Post, PostLike, Topic
from social.models import Follow


def post_list(request):
    """Instagram-like feed of forum posts"""
    topic_slug = request.GET.get("topic")
    qs = Post.objects.select_related("author", "topic").prefetch_related("likes")

    if topic_slug:
        qs = qs.filter(topic__slug=topic_slug)

    # Search
    search = request.GET.get("q")
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(content__icontains=search)

    # Add user_liked attribute for template
    if request.user.is_authenticated:
        liked_post_ids = set(PostLike.objects.filter(
            post__in=qs, user=request.user
        ).values_list("post_id", flat=True))

        # Follow status for post authors
        author_ids = set(qs.values_list("author_id", flat=True))
        followed_author_ids = set(Follow.objects.filter(
            follower=request.user, followed_id__in=author_ids
        ).values_list("followed_id", flat=True))

        for post in qs:
            post._user_liked = post.pk in liked_post_ids
            post.author.is_following = post.author.pk in followed_author_ids

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))
    topics = Topic.objects.all()

    context = {
        "page": page,
        "topics": topics,
        "selected_topic": topic_slug,
        "search": search or "",
    }

    if getattr(request, "htmx", False):
        return render(request, "agroforum/_post_grid.html", context)
    return render(request, "agroforum/post_list.html", context)


def post_detail(request, pk):
    """Post detail with nested comments"""
    post = get_object_or_404(
        Post.objects.select_related("author", "topic").prefetch_related("likes"),
        pk=pk
    )

    # Increment view count
    post.view_count += 1
    post.save(update_fields=["view_count"])

    # Get top-level comments with replies prefetched
    comments = post.comments.filter(parent__isnull=True).select_related(
        "author"
    ).prefetch_related(
        "replies__author",
        "replies__replies__author",
        "likes"
    )

    # Add user_liked attribute for comments
    if request.user.is_authenticated:
        # Post like
        post._user_liked = PostLike.objects.filter(post=post, user=request.user).exists()

        # Follow status for post author
        if request.user != post.author:
            post.author.is_following = Follow.objects.filter(
                follower=request.user, followed=post.author
            ).exists()

        # Comment likes - get all comment IDs in the tree
        all_comment_ids = []
        def collect_comment_ids(comments_qs):
            for c in comments_qs:
                all_comment_ids.append(c.pk)
                collect_comment_ids(c.replies.all())
        collect_comment_ids(comments)

        liked_comment_ids = set(CommentLike.objects.filter(
            comment_id__in=all_comment_ids, user=request.user
        ).values_list("comment_id", flat=True))

        def set_user_liked(comments_qs):
            for c in comments_qs:
                c._user_liked = c.pk in liked_comment_ids
                set_user_liked(c.replies.all())
        set_user_liked(comments)

    # Handle new comment/reply via HTMX
    if request.method == "POST" and request.headers.get("HX-Request"):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Login required"}, status=403)

        parent_id = request.POST.get("parent_id")
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.parent = parent
            comment.save()

            # Set user_liked for new comment
            comment._user_liked = False

            # Render the new comment
            if parent:
                # Render reply
                context = {"comment": comment, "user": request.user, "depth": comment.get_depth()}
                return render(request, "agroforum/_comment.html", context)
            else:
                # Render top-level comment
                context = {"comment": comment, "user": request.user}
                return render(request, "agroforum/_comment.html", context)
        else:
            return JsonResponse({"errors": form.errors}, status=400)

    comment_form = CommentForm()
    user_liked = post._user_liked if request.user.is_authenticated else False

    context = {
        "post": post,
        "comments": comments,
        "comment_form": comment_form,
        "user_liked": user_liked,
        "topics": Topic.objects.all(),
    }
    return render(request, "agroforum/post_detail.html", context)


@login_required
def post_create(request):
    """Create new forum post"""
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Your post has been published!")
            return redirect("agroforum:post_detail", pk=post.pk)
    else:
        form = PostForm()

    return render(request, "agroforum/post_form.html", {"form": form})


@login_required
def post_edit(request, pk):
    """Edit own post"""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated!")
            return redirect("agroforum:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, "agroforum/post_form.html", {"form": form, "post": post})


@login_required
@require_POST
def post_delete(request, pk):
    """Delete own post"""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    messages.success(request, "Post deleted.")
    return redirect("agroforum:post_list")


@login_required
@require_POST
def post_like(request, pk):
    """Toggle post like (HTMX)"""
    post = get_object_or_404(Post, pk=pk)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    if getattr(request, "htmx", False):
        return render(request, "agroforum/_like_button.html", {
            "post": post,
            "liked": liked,
            "user": request.user,
        })
    return redirect("agroforum:post_detail", pk=pk)


@login_required
@require_POST
def comment_like(request, pk):
    """Toggle comment like (HTMX)"""
    comment = get_object_or_404(Comment, pk=pk)
    like, created = CommentLike.objects.get_or_create(comment=comment, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    if getattr(request, "htmx", False):
        return render(request, "agroforum/_comment_like_button.html", {
            "comment": comment,
            "liked": liked,
            "user": request.user,
        })
    return redirect("agroforum:post_detail", pk=comment.post.pk)


@login_required
def comment_reply_form(request, pk):
    """Load reply form for a comment (HTMX)"""
    comment = get_object_or_404(Comment, pk=pk)
    form = CommentForm()
    return render(request, "agroforum/_reply_form.html", {
        "form": form,
        "parent_comment": comment,
        "post": comment.post,
    })


@login_required
def topic_list(request):
    """List all topics"""
    topics = Topic.objects.all()
    return render(request, "agroforum/topic_list.html", {"topics": topics})


def topic_detail(request, slug):
    """Posts in a specific topic"""
    topic = get_object_or_404(Topic, slug=slug)
    posts = topic.posts.select_related("author").prefetch_related("likes")

    # Add user_liked attribute for template
    if request.user.is_authenticated:
        liked_post_ids = set(PostLike.objects.filter(
            post__in=posts, user=request.user
        ).values_list("post_id", flat=True))

        # Follow status for post authors
        author_ids = set(posts.values_list("author_id", flat=True))
        followed_author_ids = set(Follow.objects.filter(
            follower=request.user, followed_id__in=author_ids
        ).values_list("followed_id", flat=True))

        for post in posts:
            post._user_liked = post.pk in liked_post_ids
            post.author.is_following = post.author.pk in followed_author_ids

    paginator = Paginator(posts, 10)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "topic": topic,
        "page": page,
        "topics": Topic.objects.all(),
    }
    return render(request, "agroforum/topic_detail.html", context)