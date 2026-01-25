from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

from django.utils.text import slugify
from datetime import datetime
from django.db import models
from .models import PaymentChannel
from .serializers import PaymentChannelSerializer, PaymentChannelUpdateSerializer, PaymentChannelStatsSerializer


# ------------------------
# Helpers
# ------------------------
def generate_unique_slug(name: str) -> str:
    """Generate a unique slug using name + timestamp"""
    base_slug = slugify(name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"{base_slug}-{timestamp}"


# ------------------------
# Pagination
# ------------------------
class PaymentChannelPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "per_page"
    max_page_size = 100


# ------------------------
# Create / List PaymentChannels
# ------------------------
@extend_schema(
    description="Create a payment channel (Paylink, USSD, or both). GET supports pagination and search.",
    responses={201: PaymentChannelSerializer, 400: "Validation error"},
    parameters=[
        OpenApiParameter(name="search", description="Search channels by name", required=False, type=str),
        OpenApiParameter(name="page", description="Page number for pagination", required=False, type=int),
        OpenApiParameter(name="per_page", description="Items per page", required=False, type=int),
    ],
    tags=["Payment Channels"],
)
class PaymentChannelAPIView(CreateAPIView, ListAPIView):
    """
    POST: Create a new PaymentChannel
    GET: List all channels created by the current user (with pagination & search)
    """
    serializer_class = PaymentChannelSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    pagination_class = PaymentChannelPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        """Generate unique slug and assign the user"""
        name = serializer.validated_data.get("name", "Payment")
        unique_slug = generate_unique_slug(name)
        serializer.save(user=self.request.user, slug=unique_slug)

    def get_queryset(self):
        """Return only channels created by the logged-in user"""
        return PaymentChannel.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Custom response for POST"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Payment channel created",
                "slug": serializer.instance.slug,
                "name": serializer.instance.name,
            },
            status=201,
        )

# --
# ------------------------
# Update PaymentChannel
# ------------------------

@extend_schema(
    description="Retrieve a payment channel by slug or update its name, amount, currency, or enabled methods (Paylink/USSD).",
    parameters=[
        OpenApiParameter(
            name="slug",
            description="Slug of the payment channel to retrieve or update",
            required=False,  # slug is required for this endpoint
            type=OpenApiTypes.STR
        ),
    ],
    request=PaymentChannelUpdateSerializer,
    responses=  PaymentChannelSerializer,
    tags=["Payment Channels"],
)
class PaymentChannelUpdateAPIView(RetrieveUpdateAPIView):
    serializer_class = PaymentChannelSerializer
    lookup_field = "slug"
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow access to channels created by the logged-in user
        return PaymentChannel.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """
        Return the correct serializer depending on request method
        """
        if self.request.method in ["PATCH", "PUT"]:
            return PaymentChannelUpdateSerializer
        return PaymentChannelSerializer

    def perform_update(self, serializer):
        """Save changes without modifying slug"""
        serializer.save()
