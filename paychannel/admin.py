from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from .models import PaymentChannel


admin.site.site_header = "KiviPay Administration"
admin.site.site_title = "KiviPay Admin Portal"
admin.site.index_title = "Welcome to KiviPay Admin"

# -----------------------------
# Custom Filters
# -----------------------------
class PaymentMethodFilter(SimpleListFilter):
    title = "Payment Method"
    parameter_name = "payment_method"

    def lookups(self, request, model_admin):
        return (
            ("paylink", "Paylink Enabled"),
            ("ussd", "USSD Enabled"),
            ("both", "Paylink & USSD"),
            ("none", "No Method Enabled"),
        )

    def queryset(self, request, queryset):
        if self.value() == "paylink":
            return queryset.filter(paylink_enabled=True)
        if self.value() == "ussd":
            return queryset.filter(ussd_enabled=True)
        if self.value() == "both":
            return queryset.filter(paylink_enabled=True, ussd_enabled=True)
        if self.value() == "none":
            return queryset.filter(paylink_enabled=False, ussd_enabled=False)


class ChannelAmountFilter(SimpleListFilter):
    title = "Amount Range"
    parameter_name = "amount_range"

    def lookups(self, request, model_admin):
        return (
            ("0-100", "Below 100"),
            ("100-500", "100 – 500"),
            ("500+", "Above 500"),
        )

    def queryset(self, request, queryset):
        if self.value() == "0-100":
            return queryset.filter(amount__lt=100)
        if self.value() == "100-500":
            return queryset.filter(amount__gte=100, amount__lte=500)
        if self.value() == "500+":
            return queryset.filter(amount__gt=500)


# -----------------------------
# Bulk Actions
# -----------------------------
def enable_paylink(modeladmin, request, queryset):
    queryset.update(paylink_enabled=True)
enable_paylink.short_description = "Enable Paylink"


def disable_paylink(modeladmin, request, queryset):
    queryset.update(paylink_enabled=False)
disable_paylink.short_description = "Disable Paylink"


def enable_ussd(modeladmin, request, queryset):
    queryset.update(ussd_enabled=True)
enable_ussd.short_description = "Enable USSD"


def disable_ussd(modeladmin, request, queryset):
    queryset.update(ussd_enabled=False)
disable_ussd.short_description = "Disable USSD"


# -----------------------------
# PaymentChannel Admin
# -----------------------------
@admin.register(PaymentChannel)
class PaymentChannelAdmin(admin.ModelAdmin):
    # Columns displayed in list view
    list_display = (
        "name",
        "amount",
        "currency",
        "method_status",
        "ussd",
        "user",
        "created_at",
    )

    # Make columns clickable to edit
    list_display_links = ("name", "method_status")

    # Sidebar filters
    list_filter = (
        PaymentMethodFilter,
        ChannelAmountFilter,
        "currency",
        "created_at",
    )

    # Search box
    search_fields = (
        "name",
        "slug",
        "ussd",
        "paylink",
        "user__email",
        "user__phone",
    )

    # Date navigation
    date_hierarchy = "created_at"

    # Default ordering
    ordering = ("-created_at",)

    # Pagination
    list_per_page = 25

    # Editable fields in list
    # list_editable = ("amount",)

    # Read-only fields
    readonly_fields = (
        "id",
        "slug",
        "ussd",
        "created_at",
        "updated_at",
    )

    # Performance optimization
    list_select_related = ("user",)

    # Bulk actions
    actions = (
        enable_paylink,
        disable_paylink,
        enable_ussd,
        disable_ussd,
    )

    # Method status badge
    def method_status(self, obj):
        methods = []
        if obj.paylink_enabled:
            methods.append(format_html(
                'Paylink'
            ))
        if obj.ussd_enabled:
            methods.append(format_html(
                'USSD'
            ))
        return " | ".join(methods) if methods else "None"

    method_status.short_description = "Enabled Methods"
