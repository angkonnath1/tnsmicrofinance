from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.core.validators import validate_bd_phone, validate_image_file

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin (Owner)'),
        ('OFFICER', 'Loan / Field Officer'),
        ('MEMBER', 'Member'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    phone = models.CharField(max_length=20, blank=True, null=True, validators=[validate_bd_phone])
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True, validators=[validate_image_file])
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_officer_user(self):
        return self.role == 'OFFICER'

    @property
    def is_member_user(self):
        return self.role == 'MEMBER'

    def get_role_display_badge(self):
        badges = {
            'ADMIN': 'badge-danger',
            'OFFICER': 'badge-primary',
            'MEMBER': 'badge-success',
        }
        return badges.get(self.role, 'badge-secondary')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
