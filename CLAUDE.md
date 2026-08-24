# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Django + HTMX + Tailwind livestock marketplace where:
- Anyone can browse listings without an account
- Account required to view seller WhatsApp contact details
- Only users with `is_seller=True` (set via Django admin) can post/edit listings
- No payments/checkout in-app — deals finalized via WhatsApp

## Development Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver

# Visit http://127.0.0.1:8000
```

## Project Structure

```
accounts/   Custom user model (is_seller flag), login/signup
listings/   Category, Livestock, LivestockImage models + views/templates
core/       Homepage
templates/  base.html + app templates (Tailwind via CDN, HTMX via CDN)
```

## Key Models

- **CustomUser** (`accounts/models.py`): Extends AbstractUser with `is_seller` boolean and `phone` field
- **Category** (`listings/models.py`): Name and slug for livestock categories
- **Livestock** (`listings/models.py`): Main listing model with title, category, description, price, breed, age, weight, location, status, WhatsApp number, and `posted_by` FK
- **LivestockImage** (`listings/models.py`): Multiple images per listing

## Key Views

- **listings/views.py**:
  - `listing_list`: Browse available livestock with HTMX-powered filtering/pagination
  - `listing_detail`: View listing details; WhatsApp link only shown to authenticated users
  - `listing_create` / `listing_edit`: Seller-only views (decorated with `@user_passes_test(is_seller)`)
  - `my_listings`: Seller's own listings
- **core/views.py**: Homepage with featured listings
- **accounts/views.py**: Signup view

## Authentication & Authorization

- Custom user model: `AUTH_USER_MODEL = "accounts.CustomUser"`
- Login required for seller actions (create/edit/my_listings)
- Seller check: `user.is_authenticated and user.is_seller`
- No self-service "become a seller" — admin only

## Frontend Stack

- Tailwind CSS via CDN (`<script src="https://cdn.tailwindcss.com"></script>`)
- HTMX via CDN (`<script src="https://unpkg.com/htmx.org@1.9.12"></script>`)
- HTMX used for:
  - Category filtering and search (hx-get, hx-target, hx-push-url)
  - Infinite scroll "Load more" pagination (hx-target="closest div.grid", hx-swap="beforeend")

## URLs

- `/` → core:home
- `/listings/` → listings:list (browse)
- `/listings/new/` → listings:create (seller only)
- `/listings/<pk>/` → listings:detail
- `/listings/<pk>/edit/` → listings:edit (seller only, owner only)
- `/listings/mine/` → listings:my_listings (seller only)
- `/accounts/login/`, `/accounts/logout/`, `/accounts/signup/`

## Admin Setup

1. Log in to `/admin/` with superuser
2. Go to Accounts > Users, open account, check **is_seller**, save
3. Add Category entries first (required for Livestock)

## Deployment Notes

- Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` as env vars
- Swap SQLite for Postgres in `settings.py`
- Replace Tailwind CDN with proper build for production
- Point `MEDIA_ROOT`/`MEDIA_URL` at real storage (S3) for media persistence