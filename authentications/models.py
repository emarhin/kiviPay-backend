import uuid
import re
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        null=True, 
        blank=True
    )
    phone_verified = models.BooleanField(default=False)
    
    
    
    # USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
 
    def __str__(self):
        return self.email