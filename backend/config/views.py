import re
from html import escape

from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from power.models import Area, Status
from power.serializers import effective_status

DEFAULT_TITLE = "LightDey — Is there light in your area?"
DEFAULT_DESCRIPTION = "Crowdsourced, real-time electricity supply for Nigerian neighbourhoods. Tap once to report, see who has light, and get notified when it's back."


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})


def _duration(since):
    minutes = int((timezone.now() - since).total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        return f"{hours // 24}d {hours % 24}h"
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def share_meta(path):
    """Title/description for link previews (WhatsApp, X, Facebook don't run JavaScript)."""
    match = re.match(r"^/a/([\w-]+)/?$", path)
    area = Area.objects.filter(slug=match.group(1)).first() if match else None
    if not area:
        return DEFAULT_TITLE, DEFAULT_DESCRIPTION

    state, since = effective_status(area)
    title = f"Is there light in {area.label}? — LightDey"
    if state == Status.ON:
        description = "💡 Light dey" + (f" — on for {_duration(since)}." if since else ".")
    elif state == Status.OFF:
        description = "🌑 No light" + (f" — off for {_duration(since)}." if since else ".")
    else:
        description = "No recent reports."
    return title, f"{description} Tap to see live reports and supply hours, or report for your street."


@require_GET
def spa(request):
    """Serve the React app, with per-page link-preview tags filled in."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Frontend not built. Run the Vite dev server (npm run dev) or `npm run build`.",
            status=404,
            content_type="text/plain",
        )

    title, description = share_meta(request.path)
    url = f"{settings.SITE_URL}{request.path}"
    image = f"{settings.SITE_URL}/og-image.png"
    tags = "\n    ".join([
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        f'<meta property="og:url" content="{escape(url)}" />',
        f'<meta property="og:image" content="{escape(image)}" />',
        '<meta property="og:type" content="website" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="description" content="{escape(description)}" />',
    ])
    html = index.read_text(encoding="utf-8")
    html = html.replace("<!--SHARE_META-->", tags)
    html = re.sub(r"<title>.*?</title>", f"<title>{escape(title)}</title>", html, count=1)

    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response
