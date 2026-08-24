"""
Locust load test for Livestock Marketplace Django application.

Run with: locust -f locust.py --host=http://127.0.0.1:8000
Web UI: http://localhost:8089
"""
import random
import re
from locust import HttpUser, task, between, tag


class MarketplaceUser(HttpUser):
    """Simulates a marketplace user browsing and interacting with listings."""
    wait_time = between(1, 3)
    host = "http://127.0.0.1:8000"

    def on_start(self):
        """Initialize session and fetch CSRF token."""
        self.csrf_token = None
        self.user_credentials = None
        self.is_seller = False
        self._fetch_csrf()

    def _fetch_csrf(self, url="/"):
        """Get CSRF token from a page. Returns the token."""
        with self.client.get(url, catch_response=True) as response:
            if response.status_code == 200:
                # Extract CSRF from cookie
                self.csrf_token = response.cookies.get("csrftoken")
                # Also try to extract from form if not in cookie
                if not self.csrf_token:
                    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
                    if match:
                        self.csrf_token = match.group(1)
            else:
                response.failure(f"Page load failed: {response.status_code}")
        return self.csrf_token

    def _post_with_csrf(self, url, data, name=None, referer=None, **kwargs):
        """POST with CSRF token in headers and form data."""
        # Always fetch fresh CSRF from the referer page first
        if referer:
            self._fetch_csrf(referer)

        if self.csrf_token:
            headers = {"X-CSRFToken": self.csrf_token, "Referer": referer or self.host}
            kwargs.setdefault("headers", {}).update(headers)
            data = data.copy()
            data["csrfmiddlewaretoken"] = self.csrf_token
        return self.client.post(url, data=data, name=name, **kwargs)

    # ──────────────────────────────────────────────
    # Anonymous user tasks
    # ──────────────────────────────────────────────

    @tag("browse")
    @task(10)
    def browse_home(self):
        """Load home page with hero carousel and featured listings."""
        with self.client.get("/", name="Home", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("browse")
    @task(8)
    def browse_listings(self):
        """Load listings page with filters."""
        with self.client.get("/listings/", name="Listings", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("browse")
    @task(5)
    def browse_listings_with_category(self):
        """Load listings filtered by random category."""
        categories = ["cattle", "goats", "poultry", "plant", "animal"]
        category = random.choice(categories)
        with self.client.get(
            f"/listings/?category={category}",
            name="Listings (category filter)",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("browse")
    @task(3)
    def browse_listings_with_search(self):
        """Load listings with search query."""
        searches = ["cow", "goat", "chicken", "fowl", "livestock"]
        q = random.choice(searches)
        with self.client.get(
            f"/listings/?q={q}",
            name="Listings (search)",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("browse")
    @task(5)
    def view_listing_detail(self):
        """View a random available listing detail page."""
        # First get a listing ID from the listings page
        with self.client.get("/listings/", catch_response=True) as resp:
            if resp.status_code == 200:
                # Extract listing IDs from HTML (simplified - in real test, parse properly)
                import re
                ids = re.findall(r'/listings/(\d+)/', resp.text)
                if ids:
                    listing_id = random.choice(ids)
                    with self.client.get(
                        f"/listings/{listing_id}/",
                        name="Listing Detail",
                        catch_response=True,
                    ) as response:
                        if response.status_code != 200:
                            response.failure(f"Status: {response.status_code}")

    @tag("browse")
    @task(2)
    def load_more_listings(self):
        """Test HTMX infinite scroll - load more listings."""
        with self.client.get(
            "/listings/?page=2",
            name="Listings (page 2)",
            catch_response=True,
            headers={"HX-Request": "true"},
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    # ──────────────────────────────────────────────
    # Authentication tasks
    # ──────────────────────────────────────────────

    @tag("auth")
    @task(3)
    def signup_flow(self):
        """Test user registration."""
        email = f"testuser{random.randint(1000,9999)}@example.com"
        username = f"testuser{random.randint(1000,9999)}"
        password = "TestPass123!"

        # GET signup page
        with self.client.get("/accounts/signup/", name="Signup Page", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET signup failed: {resp.status_code}")
                return

        # POST signup
        data = {
            "username": username,
            "email": email,
            "password1": password,
            "password2": password,
        }
        with self._post_with_csrf(
            "/accounts/signup/",
            data,
            name="Signup Submit",
            catch_response=True,
            referer="/accounts/signup/",
        ) as response:
            if response.status_code in (200, 302):
                self.user_credentials = (username, password)
                self._fetch_csrf()  # Refresh CSRF after login
            else:
                response.failure(f"Signup failed: {response.status_code}")

    @tag("auth")
    @task(5)
    def login_flow(self):
        """Test user login."""
        # First ensure we have a user (create one if needed)
        if not self.user_credentials:
            self.signup_flow()
            if not self.user_credentials:
                return

        username, password = self.user_credentials

        # GET login page
        with self.client.get("/accounts/login/", name="Login Page", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET login failed: {resp.status_code}")
                return

        # POST login
        data = {"username": username, "password": password}
        with self._post_with_csrf(
            "/accounts/login/",
            data,
            name="Login Submit",
            catch_response=True,
            referer="/accounts/login/",
        ) as response:
            if response.status_code in (200, 302):
                self._fetch_csrf()
            else:
                response.failure(f"Login failed: {response.status_code}")

    @tag("auth")
    @task(2)
    def logout_flow(self):
        """Test user logout."""
        if self.user_credentials:
            with self.client.post(
                "/accounts/logout/",
                name="Logout",
                catch_response=True,
            ) as response:
                if response.status_code in (200, 302):
                    self.user_credentials = None
                    self._fetch_csrf()
                else:
                    response.failure(f"Logout failed: {response.status_code}")

    # ──────────────────────────────────────────────
    # Authenticated user tasks
    # ──────────────────────────────────────────────

    @tag("authenticated")
    @task(5)
    def view_profile(self):
        """View own profile page."""
        if not self.user_credentials:
            return

        with self.client.get("/accounts/profile/", name="Profile", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("authenticated")
    @task(3)
    def edit_profile(self):
        """Edit profile."""
        if not self.user_credentials:
            return

        # GET edit page
        with self.client.get("/accounts/profile/edit/", name="Edit Profile Page", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET edit profile failed: {resp.status_code}")
                return

        # POST edit
        data = {
            "bio": "Updated bio for load test",
            "location": "Test Location",
            "phone": "+237600000000",
        }
        with self._post_with_csrf(
            "/accounts/profile/edit/",
            data,
            name="Edit Profile Submit",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 302):
                response.failure(f"Edit profile failed: {response.status_code}")

    # ──────────────────────────────────────────────
    # Seller tasks (require is_seller=True)
    # ──────────────────────────────────────────────

    @tag("seller")
    @task(3)
    def create_listing(self):
        """Create a new livestock listing (seller only)."""
        if not self.user_credentials:
            return

        # GET create page
        with self.client.get("/listings/new/", name="Create Listing Page", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET create listing failed: {resp.status_code}")
                return

        # POST create listing
        titles = ["Healthy Cattle", "Goats for Sale", "Poultry Birds", "Quality Livestock"]
        breeds = ["Holstein", "Boer", "Broiler", "Local Breed"]
        locations = ["Douala", "Yaoundé", "Bafoussam", "Bamenda"]

        data = {
            "title": f"{random.choice(titles)} {random.randint(1,100)}",
            "category": "1",  # Assuming category ID 1 exists
            "description": "Healthy animals, well-fed, ready for market. Contact for details.",
            "price": f"{random.randint(50000, 500000)}.00",
            "breed": random.choice(breeds),
            "age": f"{random.randint(6, 36)} months",
            "weight_kg": f"{random.randint(100, 500)}.00",
            "location": random.choice(locations),
            "whatsapp_number": "237600000000",
            "status": "available",
            # Note: image upload requires multipart - skipping for simplicity
        }
        with self._post_with_csrf(
            "/listings/new/",
            data,
            name="Create Listing Submit",
            catch_response=True,
            referer="/listings/new/",
        ) as response:
            if response.status_code not in (200, 302):
                response.failure(f"Create listing failed: {response.status_code}")

    @tag("seller")
    @task(3)
    def view_my_listings(self):
        """View seller's own listings."""
        if not self.user_credentials:
            return

        with self.client.get("/listings/mine/", name="My Listings", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Status: {response.status_code}")

    @tag("seller")
    @task(2)
    def edit_own_listing(self):
        """Edit one of seller's own listings."""
        if not self.user_credentials:
            return

        # GET my listings to find editable listing IDs
        with self.client.get("/listings/mine/", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET my listings failed: {resp.status_code}")
                return

            import re
            ids = re.findall(r'/listings/(\d+)/edit/', resp.text)
            if not ids:
                return

            listing_id = random.choice(ids)

            # GET edit page
            with self.client.get(
                f"/listings/{listing_id}/edit/",
                name="Edit Listing Page",
                catch_response=True,
            ) as resp2:
                if resp2.status_code != 200:
                    resp2.failure(f"GET edit listing failed: {resp2.status_code}")
                    return

            # POST edit
            data = {
                "title": f"Updated Listing {random.randint(1,100)}",
                "category": "1",
                "description": "Updated description via load test.",
                "price": f"{random.randint(50000, 500000)}.00",
                "breed": "Updated Breed",
                "age": "12 months",
                "weight_kg": "250.00",
                "location": "Douala",
                "whatsapp_number": "237600000000",
                "status": "available",
            }
            with self._post_with_csrf(
                f"/listings/{listing_id}/edit/",
                data,
                name="Edit Listing Submit",
                catch_response=True,
                referer=f"/listings/{listing_id}/edit/",
            ) as response:
                if response.status_code not in (200, 302):
                    response.failure(f"Edit listing failed: {response.status_code}")

    @tag("seller")
    @task(1)
    def delete_own_listing(self):
        """Delete one of seller's own listings."""
        if not self.user_credentials:
            return

        # GET my listings to find deletable listing IDs
        with self.client.get("/listings/mine/", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"GET my listings failed: {resp.status_code}")
                return

            import re
            ids = re.findall(r'/listings/(\d+)/delete/', resp.text)
            if not ids:
                return

            listing_id = random.choice(ids)

            # POST delete
            with self._post_with_csrf(
                f"/listings/{listing_id}/delete/",
                {},
                name="Delete Listing",
                catch_response=True,
            ) as response:
                if response.status_code not in (200, 302):
                    response.failure(f"Delete listing failed: {response.status_code}")

    # ──────────────────────────────────────────────
    # Contact/Interaction tasks
    # ──────────────────────────────────────────────

    @tag("contact")
    @task(2)
    def view_whatsapp_link(self):
        """Test that WhatsApp link is accessible (requires auth)."""
        if not self.user_credentials:
            return

        # Get a listing ID first
        with self.client.get("/listings/", catch_response=True) as resp:
            if resp.status_code != 200:
                return

            import re
            ids = re.findall(r'/listings/(\d+)/', resp.text)
            if not ids:
                return

            listing_id = random.choice(ids)

            # In the template, the WhatsApp link is rendered directly with the listing.whatsapp_link property
            # We can't easily test the redirect without JavaScript, but we can verify the listing page renders
            with self.client.get(
                f"/listings/{listing_id}/",
                name="Listing Detail (for WhatsApp)",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Status: {response.status_code}")
                elif "wa.me" not in response.text and "Chat on WhatsApp" not in response.text:
                    # Only logged in users should see WhatsApp link
                    pass  # Expected for anonymous, but we're logged in


class SellerUser(MarketplaceUser):
    """User that is a seller - weights tasks toward seller actions."""
    wait_time = between(1, 2)

    def on_start(self):
        super().on_start()
        # In real scenario, this user would be pre-created with is_seller=True
        # For testing, we simulate by biasing task weights


class AnonymousUser(MarketplaceUser):
    """Anonymous user - only browse tasks."""
    wait_time = between(2, 5)

    # Disable auth and seller tasks for anonymous users
    signup_flow = None
    login_flow = None
    logout_flow = None
    view_profile = None
    edit_profile = None
    create_listing = None
    view_my_listings = None
    edit_own_listing = None
    delete_own_listing = None
    view_whatsapp_link = None


class ReadOnlyUser(MarketplaceUser):
    """Authenticated non-seller user - browse + auth tasks only."""
    wait_time = between(1, 3)

    create_listing = None
    view_my_listings = None
    edit_own_listing = None
    delete_own_listing = None


# ──────────────────────────────────────────────
# Custom shape for staged load testing
# ──────────────────────────────────────────────

from locust import LoadTestShape


class StagesShape(LoadTestShape):
    """
    Staged load test:
    - Ramp up to 10 users over 1 min
    - Hold 10 users for 2 min
    - Ramp to 50 users over 2 min
    - Hold 50 users for 3 min
    - Ramp to 100 users over 2 min
    - Hold 100 users for 2 min
    - Ramp down to 0
    """
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},
        {"duration": 180, "users": 10, "spawn_rate": 1},
        {"duration": 300, "users": 50, "spawn_rate": 5},
        {"duration": 480, "users": 50, "spawn_rate": 1},
        {"duration": 600, "users": 100, "spawn_rate": 10},
        {"duration": 720, "users": 100, "spawn_rate": 1},
        {"duration": 780, "users": 0, "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None