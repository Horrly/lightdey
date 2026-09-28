from django.contrib import admin
from django.urls import path, re_path

from power.views import (
    AreaDetailView,
    AreaListView,
    OverviewView,
    PushConfigView,
    PushSubscribeView,
    ReportView,
)

from .views import health, spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/overview/", OverviewView.as_view(), name="overview"),
    path("api/areas/", AreaListView.as_view(), name="areas"),
    path("api/areas/<slug:slug>/", AreaDetailView.as_view(), name="area-detail"),
    path("api/areas/<slug:slug>/reports/", ReportView.as_view(), name="area-report"),
    path("api/areas/<slug:slug>/push/", PushSubscribeView.as_view(), name="area-push"),
    path("api/push/config/", PushConfigView.as_view(), name="push-config"),
    # Everything else is a React route.
    re_path(r"^(?!api/|admin/|static/).*$", spa, name="spa"),
]
