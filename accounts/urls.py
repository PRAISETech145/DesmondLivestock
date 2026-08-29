from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.EmailVerifiedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="listings:list"), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("verify-email/sent/", views.verify_email_sent, name="verify_email_sent"),
    path("verify-email/resend/", views.resend_verification, name="resend_verification"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile, name="profile"),
]