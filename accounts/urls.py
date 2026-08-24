from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="listings:list"), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("manage-sellers/", views.manage_sellers, name="manage_sellers"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile, name="profile"),
]