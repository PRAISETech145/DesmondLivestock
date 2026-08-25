from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import LivestockForm
from .models import Category, Livestock


def listing_list(request):
    qs = Livestock.objects.filter(status="available").select_related("category", "posted_by")

    # Category filter
    category_slug = request.GET.get("category")
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    # Search
    search = request.GET.get("q")
    if search:
        qs = qs.filter(title__icontains=search)

    # Price range
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    if min_price:
        qs = qs.filter(price__gte=min_price)
    if max_price:
        qs = qs.filter(price__lte=max_price)

    # Location filter
    location = request.GET.get("location")
    if location:
        qs = qs.filter(location__icontains=location)

    # Breed filter
    breed = request.GET.get("breed")
    if breed:
        qs = qs.filter(breed__icontains=breed)

    # Status filter (override default "available")
    status = request.GET.get("status")
    if status:
        qs = Livestock.objects.filter(status=status).select_related("category", "posted_by")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if search:
            qs = qs.filter(title__icontains=search)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if location:
            qs = qs.filter(location__icontains=location)
        if breed:
            qs = qs.filter(breed__icontains=breed)

    # Verified seller filter
    verified = request.GET.get("verified")
    if verified:
        qs = qs.filter(posted_by__is_verified=True)

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))
    categories = Category.objects.all()

    # Get unique locations for filter dropdown
    locations = Livestock.objects.filter(status="available").values_list("location", flat=True).distinct().order_by("location")
    # Get unique breeds for filter dropdown
    breeds = Livestock.objects.filter(status="available").exclude(breed="").values_list("breed", flat=True).distinct().order_by("breed")

    context = {
        "page": page,
        "categories": categories,
        "selected_category": category_slug,
        "search": search or "",
        "min_price": min_price or "",
        "max_price": max_price or "",
        "location": location or "",
        "breed": breed or "",
        "status": status or "",
        "verified": verified or "",
        "locations": locations,
        "breeds": breeds,
    }

    if getattr(request, "htmx", False):
        return render(request, "listings/_grid.html", context)
    return render(request, "listings/list.html", context)


def listing_detail(request, pk):
    listing = get_object_or_404(Livestock.objects.select_related("category"), pk=pk)
    context = {"listing": listing, "can_contact": request.user.is_authenticated}
    return render(request, "listings/detail.html", context)


@login_required
def listing_create(request):
    if request.method == "POST":
        form = LivestockForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.posted_by = request.user
            listing.save()
            messages.success(request, "Your livestock listing has been posted successfully!")
            return redirect("core:home")
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = LivestockForm()
    return render(request, "listings/form.html", {"form": form})


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Livestock, pk=pk, posted_by=request.user)
    if request.method == "POST":
        form = LivestockForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            return redirect("listings:detail", pk=listing.pk)
    else:
        form = LivestockForm(instance=listing)
    return render(request, "listings/form.html", {"form": form, "listing": listing})


@login_required
def my_listings(request):
    qs = Livestock.objects.filter(posted_by=request.user)
    return render(request, "listings/my_listings.html", {"listings": qs})


@login_required
@require_POST
def listing_delete(request, pk):
    listing = get_object_or_404(Livestock, pk=pk, posted_by=request.user)
    listing.delete()
    messages.success(request, "Listing deleted successfully.")
    return redirect("listings:my_listings")