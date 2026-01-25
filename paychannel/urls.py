from django.urls import path
from .views import (
    PaymentChannelAPIView,
    # PaymentChannelStatsAPIView,
    PaymentChannelUpdateAPIView
)

urlpatterns = [
    # API to create or list payment channels (Paylink, USSD, or both)
    path("channels/", PaymentChannelAPIView.as_view(), name="payment-channel-list-create"),  # GET + POST

    # API to get stats for all payment channels
    # path("channels/stats/", PaymentChannelStatsAPIView.as_view(), name="payment-channel-stats"),

    # API to retrieve or update a specific channel by slug
    path("channels/<slug:slug>/", PaymentChannelUpdateAPIView.as_view(), name="payment-channel-update"),  # GET, PATCH, PUT
]
