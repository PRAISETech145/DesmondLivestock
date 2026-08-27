from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from .models import Follow


def user_list(request):
    """Show people page with Following and Followers tabs."""
    if not request.user.is_authenticated:
        # Redirect to login or show public discover page
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")

    # Get users the current user follows (Follow objects)
    following_qs = request.user.following.select_related("followed").order_by("-created_at")

    # Get users who follow the current user (Follow objects)
    followers_qs = request.user.followers.select_related("follower").order_by("-created_at")

    # Search
    search = request.GET.get("q")
    if search:
        from django.db.models import Q
        following_qs = following_qs.filter(
            Q(followed__username__icontains=search) |
            Q(followed__first_name__icontains=search) |
            Q(followed__last_name__icontains=search)
        )
        followers_qs = followers_qs.filter(
            Q(follower__username__icontains=search) |
            Q(follower__first_name__icontains=search) |
            Q(follower__last_name__icontains=search)
        )

    # Add follow status: for following tab, we already follow them (True).
    # For followers tab, check if we follow them back.
    if request.user.is_authenticated:
        following_ids = set(request.user.following.values_list("followed_id", flat=True))

        # For following tab: we follow all of them
        for follow in following_qs:
            follow.followed.is_following = True
            follow.followed.is_self = (follow.followed.pk == request.user.pk)

        # For followers tab: check if we follow them back
        for follow in followers_qs:
            follow.follower.is_following = follow.follower.pk in following_ids
            follow.follower.is_self = (follow.follower.pk == request.user.pk)

    # Paginate both
    following_paginator = Paginator(following_qs, 20)
    followers_paginator = Paginator(followers_qs, 20)

    following_page = following_paginator.get_page(request.GET.get("following_page"))
    followers_page = followers_paginator.get_page(request.GET.get("followers_page"))

    tab = request.GET.get("tab", "following")

    context = {
        "following_page": following_page,
        "followers_page": followers_page,
        "active_tab": tab,
        "search": search or "",
    }

    if getattr(request, "htmx", False):
        if tab == "followers":
            return render(request, "social/_follow_list.html", {"page": followers_page, "tab": "followers", "profile_user": request.user, "search": search or ""})
        return render(request, "social/_follow_list.html", {"page": following_page, "tab": "following", "profile_user": request.user, "search": search or ""})

    return render(request, "social/user_list.html", context)


def user_detail(request, username):
    """User profile with follow button and followers/following tabs."""
    user_obj = get_object_or_404(
        CustomUser.objects.annotate(
            followers_count=Count("followers", distinct=True),
            following_count=Count("following", distinct=True),
        ),
        username=username,
    )

    is_following = False
    is_self = request.user == user_obj

    if request.user.is_authenticated and not is_self:
        is_following = Follow.objects.filter(
            follower=request.user, followed=user_obj
        ).exists()

    tab = request.GET.get("tab", "followers")

    # Get followers and following for tabs with search
    search = request.GET.get("q")
    if tab == "followers":
        qs = user_obj.followers.select_related("follower")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(follower__username__icontains=search) |
                Q(follower__first_name__icontains=search) |
                Q(follower__last_name__icontains=search)
            )
        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get("page"))
    else:
        qs = user_obj.following.select_related("followed")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(followed__username__icontains=search) |
                Q(followed__first_name__icontains=search) |
                Q(followed__last_name__icontains=search)
            )
        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get("page"))

    context = {
        "profile_user": user_obj,
        "is_following": is_following,
        "is_self": is_self,
        "tab": tab,
        "page": page,
        "search": search or "",
    }
    return render(request, "social/user_detail.html", context)


@login_required
@require_POST
def follow_user(request, username):
    """Follow a user (HTMX) - redirect to people page with success message."""
    target = get_object_or_404(CustomUser, username=username)

    if target == request.user:
        if getattr(request, "htmx", False):
            return JsonResponse({"error": "Cannot follow yourself"}, status=400)
        messages.error(request, "You cannot follow yourself.")
        return redirect("social:user_list")

    follow, created = Follow.objects.get_or_create(
        follower=request.user, followed=target
    )

    if not created:
        follow.delete()
        is_following = False
        action = "unfollowed"
    else:
        is_following = True
        action = "followed"

    # Add success message
    messages.success(request, f"You have {action} {target.username}.")

    # Always redirect to people page to show the updated follow lists
    return redirect("social:user_list")


def user_followers(request, username):
    """List users who follow the given user."""
    user_obj = get_object_or_404(CustomUser, username=username)
    followers = user_obj.followers.select_related("follower")

    # Search
    search = request.GET.get("q")
    if search:
        from django.db.models import Q
        followers = followers.filter(
            Q(follower__username__icontains=search) |
            Q(follower__first_name__icontains=search) |
            Q(follower__last_name__icontains=search)
        )

    paginator = Paginator(followers, 20)
    page = paginator.get_page(request.GET.get("page"))

    context = {"profile_user": user_obj, "page": page, "tab": "followers", "search": search or ""}
    return render(request, "social/_follow_list.html", context)


def user_following(request, username):
    """List users the given user follows."""
    user_obj = get_object_or_404(CustomUser, username=username)
    following = user_obj.following.select_related("followed")

    # Search
    search = request.GET.get("q")
    if search:
        from django.db.models import Q
        following = following.filter(
            Q(followed__username__icontains=search) |
            Q(followed__first_name__icontains=search) |
            Q(followed__last_name__icontains=search)
        )

    paginator = Paginator(following, 20)
    page = paginator.get_page(request.GET.get("page"))

    context = {"profile_user": user_obj, "page": page, "tab": "following", "search": search or ""}
    return render(request, "social/_follow_list.html", context)