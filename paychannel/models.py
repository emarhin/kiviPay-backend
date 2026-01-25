from django.db import models
import uuid
from django.utils.text import slugify


class PaymentChannel(models.Model):
    """
    Represents a reusable payment channel which can support Paylink, USSD, or both.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUID primary key
    
    name = models.CharField(max_length=255, default="Payment")
    slug = models.CharField(max_length=100, unique=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='GHS')
    
    user = models.ForeignKey("authentications.CustomUser", on_delete=models.CASCADE, related_name="payment_channels")

    # Payment methods
    paylink_enabled = models.BooleanField(default=True)
    paylink = models.URLField(blank=True, null=True)

    ussd_enabled = models.BooleanField(default=True)
    ussd = models.CharField(max_length=20, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{uuid.uuid4().hex[:6]}")
        if not self.ussd:
            self.ussd = generate_ussd_code()
    
        super().save(*args, **kwargs)

    def __str__(self):
        methods = []
        if self.paylink_enabled and self.paylink:
            methods.append("Paylink")
        if self.ussd_enabled and self.ussd:
            methods.append("USSD")
        method_str = " & ".join(methods) if methods else "No method enabled"
        return f"{self.name} ({method_str}) - {self.amount} {self.currency}"
    
    
def generate_ussd_code():
    """
    Generate the lowest available unique USSD code for PaymentChannel.
    Starts from 1 and fills any gaps in existing codes.
    Returns the code as a string.
    """
    existing_codes = (
        PaymentChannel.objects.exclude(ussd__isnull=True)
        .exclude(ussd__exact="")
        .values_list("ussd", flat=True)
    )

    # Convert existing codes to a set of integers
    existing_codes_set = set()
    for code in existing_codes:
        if code.isdigit():
            existing_codes_set.add(int(code))

    # Find the smallest available number starting from 1
    code = 1
    while code in existing_codes_set:
        code += 1

    return str(code)

