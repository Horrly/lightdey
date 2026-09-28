from django.contrib import admin

from .models import Area, PushSubscription, Report


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "state", "status", "last_report_at"]
    list_filter = ["state", "status"]
    search_fields = ["name", "city"]
    readonly_fields = ["status", "status_since", "last_report_at", "last_notified_at", "created_by_hash"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["area", "state", "created_at"]
    list_filter = ["state"]
    date_hierarchy = "created_at"


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["area", "created_at"]
