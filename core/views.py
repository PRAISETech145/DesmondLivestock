from django.shortcuts import render
from listings.models import Livestock, Category


def home(request):
    featured = Livestock.objects.filter(status="available").select_related("category")[:6]
    categories = Category.objects.all()
    return render(request, "core/home.html", {"featured": featured, "categories": categories})
