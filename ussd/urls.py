from django.urls import path
from .views import ussd_handler

urlpatterns = [
    path("ussd/", ussd_handler),
]
