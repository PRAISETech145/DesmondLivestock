from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
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


