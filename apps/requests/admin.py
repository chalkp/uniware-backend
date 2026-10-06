from django.contrib import admin

from .models import BorrowerRequest


@admin.register(BorrowerRequest)
class BorrowerRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "borrower",
        "equipment",
        "status",
        "pickup_date",
        "due_date",
        "decided_by",
    ]
    list_filter = ["status", "pickup_date", "due_date"]
    search_fields = [
        "borrower__email",
        "equipment__name",
        "equipment__asset_id",
    ]
    readonly_fields = ["decided_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("borrower", "equipment", "decided_by")
