from django.conf import settings
from django.http import JsonResponse, HttpResponse

class LocalOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        remote = request.META.get('REMOTE_ADDR', '')
        origin = request.headers.get('Origin')
        if remote not in ('127.0.0.1', '::1', ''):
            return JsonResponse({'detail': 'TLDR only accepts local connections.'}, status=403)
        if origin and origin not in settings.LOCAL_ORIGINS:
            return JsonResponse({'detail': 'Origin is not allowed.'}, status=403)
        if request.headers.get('Sec-Fetch-Site') == 'cross-site' and not origin:
            return JsonResponse({'detail': 'Cross-site requests are not allowed.'}, status=403)
        response = HttpResponse(status=204) if request.method == 'OPTIONS' else self.get_response(request)
        if origin:
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, DELETE, OPTIONS'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-store'
        return response
