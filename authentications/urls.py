# config/urls.py
from django.urls import path, include



urlpatterns = [
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Add this line to register allauth endpoints
    path('accounts/', include('allauth.urls')),   # required for internal allauth usage
    

    
]
