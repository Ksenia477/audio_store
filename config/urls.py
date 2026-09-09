"""Project URL routes."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import healthcheck

urlpatterns = [
    path('healthz/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('', include('catalog.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
