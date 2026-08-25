# Livestock Market

Django + HTMX + Tailwind marketplace where:
- Anyone can browse listings without an account.
- An account is required to view seller WhatsApp contact details.
- Any authenticated user can post/edit listings.
- No payments/checkout in-app — buyer and seller finalize the deal on WhatsApp.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://127.0.0.1:8000

## Add categories first

In /admin/, add a few `Category` entries (e.g. Cattle, Goats, Sheep, Poultry) before posting listings — `Livestock.category` is required.

## Project layout

```
accounts/   custom user model, login/signup, profile
listings/   Category, Livestock models + views/templates
core/       homepage
templates/  base.html + app templates (Tailwind via CDN, HTMX via CDN)
```

## Before deploying

- Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` as environment variables.
- Swap SQLite for Postgres in `settings.py` (`DATABASES`).
- Swap the Tailwind CDN `<script>` in `templates/base.html` for a proper build if you want smaller page weight / custom design tokens.
- Point `MEDIA_ROOT`/`MEDIA_URL` at real storage (e.g. S3) since local media won't persist on most hosts.
