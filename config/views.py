"""Project-level utility views."""

from django.conf import settings
from django.http import JsonResponse


def healthcheck(request):
    return JsonResponse(
        {
            "status": "ok",
            "version": settings.APP_VERSION,
        }
    )
