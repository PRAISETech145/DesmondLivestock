from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import set_language

urlpatterns = [
    path("i18n/", set_language, name="set_language"),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("listings/", include("listings.urls")),
    path("accounts/", include("accounts.urls")),
    path("forum/", include("agroforum.urls")),
    path("people/", include("social.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
