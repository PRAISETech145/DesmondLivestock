import secrets

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ProfileForm, SignUpForm
from .models import CustomUser


class EmailVerifiedLoginView(LoginView):
    """Login view that requires email verification"""
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if not user.email_verified:
            form.add_error(None, "Please verify your email address before logging in. Check your inbox for the verification link.")
            return self.form_invalid(form)
        return super().form_valid(form)


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Generate and send email verification token
            send_verification_email(user, request)
            # Don't log in the user until they verify their email
            return redirect("accounts:verify_email_sent")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def send_verification_email(user, request):
    """Generate token and send verification email"""
    token = secrets.token_urlsafe(32)
    user.email_verification_token = token
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_token", "email_verification_sent_at"])

    verification_url = request.build_absolute_uri(
        f"/accounts/verify-email/{token}/"
    )

    subject = "Verify your email address - Livestock Marketplace"
    message = f"""
Hi {user.username},

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account, you can safely ignore this email.

Thanks,
The Livestock Marketplace Team
    """

    try:
        send_mail(
            subject,
            message,
            None,  # Uses DEFAULT_FROM_EMAIL
            [user.email],
            #
        )
    except Exception:
        # Log error but don't fail the signup
        pass


def verify_email(request, token):
    """Verify user's email with token"""
    try:
        user = CustomUser.objects.get(email_verification_token=token)
    except CustomUser.DoesNotExist:
        return render(request, "accounts/verify_email.html", {
            "success": False,
            "message": "Invalid or expired verification link."
        })

    # Check if token is older than 24 hours
    if user.email_verification_sent_at:
        elapsed = timezone.now() - user.email_verification_sent_at
        if elapsed.total_seconds() > 24 * 3600:
            return render(request, "accounts/verify_email.html", {
                "success": False,
                "message": "Verification link has expired. Please request a new one."
            })

    # Verify the email
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None
    user.save(update_fields=["email_verified", "email_verification_token", "email_verification_sent_at"])

    return render(request, "accounts/verify_email.html", {
        "success": True,
        "message": "Email verified successfully! You can now log in."
    })


def verify_email_sent(request):
    """Page shown after signup, telling user to check their email"""
    return render(request, "accounts/verify_email_sent.html")


def resend_verification(request):
    """Resend verification email"""
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = CustomUser.objects.get(email=email)
            if not user.email_verified:
                send_verification_email(user, request)
            # Always show success to prevent email enumeration
            return render(request, "accounts/verify_email_sent.html", {
                "resent": True
            })
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists
            return render(request, "accounts/verify_email_sent.html", {
                "resent": True
            })
    return render(request, "accounts/resend_verification.html")


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


