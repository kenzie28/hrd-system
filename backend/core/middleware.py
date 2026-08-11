from django.conf import settings
from django.http import JsonResponse

API_KEY_HEADER = 'HTTP_X_API_KEY'


class ApiKeyMiddleware:
    """Requires a matching `X-Api-Key` header on every `/api/` request.

    Enforcement only happens when `settings.API_KEY` is configured (set via
    the `API_KEY` env var). This keeps plain local dev (`dev/dev.sh`, no
    Docker) working without needing a key, while the Docker Compose stack
    always sets one.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.API_KEY and request.path.startswith('/api/'):
            provided = request.META.get(API_KEY_HEADER, '')
            if provided != settings.API_KEY:
                return JsonResponse(
                    {'detail': 'Invalid or missing API key.'}, status=401
                )
        return self.get_response(request)
