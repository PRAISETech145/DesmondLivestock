from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, SignUpForm
from .models import CustomUser


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            next_url = request.GET.get("next") or "listings:list"
            return redirect(next_url)
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request, username=None):
    """View a user's profile"""
    if username:
        user = get_object_or_404(CustomUser, username=username)
    else:
        user = request.user

    from listings.models import Livestock
    listings = Livestock.objects.filter(posted_by=user).select_related("category")

    return render(request, "accounts/profile.html", {
        "profile_user": user,
        "listings": listings,
        "is_own_profile": user == request.user,
    })


@login_required
def edit_profile(request):
    """Edit own profile"""
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def manage_sellers(request):
    """Admin page to manage who can be sellers - superuser only"""
    if not request.user.is_superuser:
        raise PermissionDenied

    users = CustomUser.objects.all().order_by("-date_joined")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        user = get_object_or_404(CustomUser, pk=user_id)

        if action == "make_seller":
            user.is_seller = True
            user.save()
        elif action == "remove_seller":
            user.is_seller = False
            user.save()
        elif action == "toggle_seller":
            user.is_seller = not user.is_seller
            user.save()

        return redirect("accounts:manage_sellers")

    return render(request, "accounts/manage_sellers.html", {"users": users})