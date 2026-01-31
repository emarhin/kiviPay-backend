from django.contrib import admin
from .models import Payment
from django.contrib.admin import SimpleListFilter
# Register your models here.

# admin.site.register(Payment)








class AmountRangeFilter(SimpleListFilter):
    title = "Amount Range"
    parameter_name = "amount_range"

    def lookups(self, request, model_admin):
        return (
            ("0-50", "Below 50"),
            ("50-200", "50 – 200"),
            ("200+", "Above 200"),
        )

    def queryset(self, request, queryset):
        if self.value() == "0-50":
            return queryset.filter(amount__lt=50)
        if self.value() == "50-200":
            return queryset.filter(amount__gte=50, amount__lte=200)
        if self.value() == "200+":
            return queryset.filter(amount__gt=200)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # List view columns
    list_display = (
        "reference",
        "amount",
        "status",
        "charge_type",
        "channel_type",
        "phone_number",
        "email",
        "created_at",
    )

    # Sidebar filters
    list_filter = (
        "status",
        "channel_type",
        "charge_type",
        AmountRangeFilter,
        "created_at",
    )

    # Search bar (fast + useful)
    search_fields = (
        "reference",
        "phone_number",
        "email",
        "channel__name",
    )

    # Date navigation (Year / Month / Day)
    date_hierarchy = "created_at"

    # Default ordering
    ordering = ("-created_at",)

    # Pagination
    list_per_page = 25

    # Read-only fields
    readonly_fields = (
        "id",
        "reference",
        "created_at",
    )

    # Performance optimization
    list_select_related = ("channel",)

    # Editable fields in list view
    # list_editable = ("status",)

    # Admin actions
    actions = (
        "mark_as_success",
        "mark_as_failed",
        "mark_as_reversed",
    )

