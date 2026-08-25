from django.urls import path

from . import views

app_name = "social"

urlpatterns = [
    path("", views.user_list, name="user_list"),
    path("u/<str:username>/", views.user_detail, name="user_detail"),
    path("u/<str:username>/followers/", views.user_followers, name="user_followers"),
    path("u/<str:username>/following/", views.user_following, name="user_following"),
    path("follow/<str:username>/", views.follow_user, name="follow_user"),
]