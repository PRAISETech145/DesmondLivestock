import logging
import random
import secrets

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProfileForm, SignUpForm
from .models import CustomUser

logger = logging.getLogger(__name__)

# Rate limit constants
SIGNUP_RATE_LIMIT = 5  # per IP per hour
RESEND_RATE_LIMIT = 3  # per email per hour
VERIFY_ATTEMPTS_LIMIT = 5  # per user
CODE_EXPIRY_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60


class EmailVerifiedLoginView(LoginView):
    """Login view that requires email verification"""
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if not user.email_verified:
            form.add_error(None, "Please verify your email address before logging in. Check your inbox for the verification code.")
            return self.form_invalid(form)
        return super().form_valid(form)


def generate_verification_code():
    """Generate a 6-digit numeric code"""
    return f"{random.randint(100000, 999999)}"


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def check_signup_rate_limit(request):
    """Check if IP has exceeded signup rate limit"""
    ip = get_client_ip(request)
    cache_key = f"signup_rate_limit:{ip}"
    count = cache.get(cache_key, 0)
    return count < SIGNUP_RATE_LIMIT


def increment_signup_rate_limit(request):
    """Increment signup rate limit counter for IP"""
    ip = get_client_ip(request)
    cache_key = f"signup_rate_limit:{ip}"
    count = cache.get(cache_key, 0)
    cache.set(cache_key, count + 1, 3600)  # 1 hour


def check_resend_rate_limit(email):
    """Check if email has exceeded resend rate limit"""
    cache_key = f"resend_rate_limit:{email}"
    count = cache.get(cache_key, 0)
    return count < RESEND_RATE_LIMIT


def increment_resend_rate_limit(email):
    """Increment resend rate limit counter for email"""
    cache_key = f"resend_rate_limit:{email}"
    count = cache.get(cache_key, 0)
    cache.set(cache_key, count + 1, 3600)  # 1 hour


def check_resend_cooldown(user):
    """Check if resend cooldown is active for user"""
    if user.email_verification_code_sent_at:
        elapsed = timezone.now() - user.email_verification_code_sent_at
        return elapsed.total_seconds() < RESEND_COOLDOWN_SECONDS
    return False


def send_verification_code_email(user, request, is_resend=False):
    """Generate 6-digit code and send verification email"""
    code = generate_verification_code()

    user.email_verification_code = code
    user.email_verification_code_sent_at = timezone.now()
    user.email_verification_code_attempts = 0
    user.save(update_fields=["email_verification_code", "email_verification_code_sent_at", "email_verification_code_attempts"])

    subject = "Your Verification Code - Livestock Marketplace"
    message = f"""
Hi {user.username},

Your verification code is: <strong style="font-size: 24px; letter-spacing: 4px; font-family: monospace;">{code}</strong>

Enter this 6-digit code on the verification page to complete your registration.

This code will expire in {CODE_EXPIRY_MINUTES} minutes.

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
            html_message=message,
        )
        logger.info(f"Verification code sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        # Don't fail the signup, but log the error


def signup(request):
    if request.method == "POST":
        # Check rate limit
        if not check_signup_rate_limit(request):
            form = SignUpForm(request.POST)
            form.add_error(None, "Too many signup attempts from this IP. Please try again later.")
            return render(request, "accounts/signup.html", {"form": form})

        form = SignUpForm(request.POST)
        if form.is_valid():
            # Check if email already exists and is verified
            email = form.cleaned_data.get('email')
            existing_user = CustomUser.objects.filter(email=email).first()
            if existing_user and existing_user.email_verified:
                form.add_error('email', "An account with this email already exists. Please log in instead.")
                return render(request, "accounts/signup.html", {"form": form})
            elif existing_user and not existing_user.email_verified:
                # Delete unverified duplicate to allow fresh signup
                existing_user.delete()

            user = form.save()
            # Generate and send email verification code
            send_verification_code_email(user, request)
            increment_signup_rate_limit(request)
            # Store user ID in session for verification page
            request.session['pending_verification_user_id'] = user.id
            return redirect("accounts:verify_email")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def verify_email(request):
    """Page where user enters 6-digit verification code"""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return redirect("accounts:signup")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        # Clean up stale session
        request.session.pop('pending_verification_user_id', None)
        return redirect("accounts:signup")

    if user.email_verified:
        del request.session['pending_verification_user_id']
        return redirect("accounts:login")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        # Validate code format
        if len(code) != 6 or not code.isdigit():
            error_msg = "Please enter a valid 6-digit code."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "error": error_msg, "valid": False})
            return render(request, "accounts/verify_email.html", {
                "error": error_msg,
                "email": user.email,
            })

        # Check if code is expired (15 minutes)
        if user.email_verification_code_sent_at:
            elapsed = timezone.now() - user.email_verification_code_sent_at
            if elapsed.total_seconds() > CODE_EXPIRY_MINUTES * 60:
                error_msg = f"Verification code has expired ({CODE_EXPIRY_MINUTES} minutes). Please request a new one."
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "error": error_msg, "expired": True})
                return render(request, "accounts/verify_email.html", {
                    "error": error_msg,
                    "expired": True,
                    "email": user.email,
                })

        # Check max attempts (5 attempts)
        if user.email_verification_code_attempts >= VERIFY_ATTEMPTS_LIMIT:
            error_msg = f"Too many failed attempts ({VERIFY_ATTEMPTS_LIMIT}). Please request a new code."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "error": error_msg, "max_attempts": True})
            return render(request, "accounts/verify_email.html", {
                "error": error_msg,
                "max_attempts": True,
                "email": user.email,
            })

        if code == user.email_verification_code:
            # Code matches - verify the email
            user.email_verified = True
            user.email_verification_code = None
            user.email_verification_code_sent_at = None
            user.email_verification_code_attempts = 0
            user.save(update_fields=["email_verified", "email_verification_code", "email_verification_code_sent_at", "email_verification_code_attempts"])

            # Clear session
            del request.session['pending_verification_user_id']

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": True, "redirect_url": "/accounts/login/"})

            return render(request, "accounts/verify_email.html", {
                "success": True,
                "message": "Email verified successfully! You can now log in."
            })
        else:
            # Increment failed attempts
            user.email_verification_code_attempts += 1
            user.save(update_fields=["email_verification_code_attempts"])

            remaining = VERIFY_ATTEMPTS_LIMIT - user.email_verification_code_attempts
            error_msg = f"Invalid code. {remaining} attempts remaining."

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "error": error_msg, "attempts_remaining": remaining})

            return render(request, "accounts/verify_email.html", {
                "error": error_msg,
                "attempts_remaining": remaining,
                "email": user.email,
            })

    return render(request, "accounts/verify_email.html", {
        "email": user.email,
    })


@require_POST
def verify_email_ajax(request):
    """AJAX endpoint for real-time code verification (auto-submit)"""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        return JsonResponse({"success": False, "error": "Session expired. Please sign up again."})

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        request.session.pop('pending_verification_user_id', None)
        return JsonResponse({"success": False, "error": "User not found."})

    if user.email_verified:
        del request.session['pending_verification_user_id']
        return JsonResponse({"success": True, "redirect_url": "/accounts/login/"})

    code = request.POST.get("code", "").strip()

    if len(code) != 6 or not code.isdigit():
        return JsonResponse({"success": False, "valid": False})

    # Check if code is expired
    if user.email_verification_code_sent_at:
        elapsed = timezone.now() - user.email_verification_code_sent_at
        if elapsed.total_seconds() > CODE_EXPIRY_MINUTES * 60:
            return JsonResponse({"success": False, "error": "Code expired", "expired": True})

    # Check max attempts
    if user.email_verification_code_attempts >= VERIFY_ATTEMPTS_LIMIT:
        return JsonResponse({"success": False, "error": "Max attempts reached", "max_attempts": True})

    if code == user.email_verification_code:
        # Code matches - verify the email
        user.email_verified = True
        user.email_verification_code = None
        user.email_verification_code_sent_at = None
        user.email_verification_code_attempts = 0
        user.save(update_fields=["email_verified", "email_verification_code", "email_verification_code_sent_at", "email_verification_code_attempts"])

        del request.session['pending_verification_user_id']

        return JsonResponse({"success": True, "redirect_url": "/accounts/login/"})
    else:
        user.email_verification_code_attempts += 1
        user.save(update_fields=["email_verification_code_attempts"])

        return JsonResponse({
            "success": False,
            "valid": False,
            "attempts_remaining": VERIFY_ATTEMPTS_LIMIT - user.email_verification_code_attempts
        })


def resend_verification(request):
    """Resend verification code"""
    user_id = request.session.get('pending_verification_user_id')

    if request.method == "POST":
        if user_id:
            # Resend for pending user
            try:
                user = CustomUser.objects.get(id=user_id)
                if not user.email_verified:
                    send_verification_code_email(user, request, is_resend=True)
            except CustomUser.DoesNotExist:
                pass
        else:
            # Resend by email input
            email = request.POST.get("email")
            try:
                user = CustomUser.objects.get(email=email)
                if not user.email_verified:
                    request.session['pending_verification_user_id'] = user.id
                    send_verification_code_email(user, request, is_resend=True)
            except CustomUser.DoesNotExist:
                # Don't reveal if email exists
                pass

        return redirect("accounts:verify_email")

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