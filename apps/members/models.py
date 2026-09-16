from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from apps.core.validators import (
    validate_bd_phone,
    validate_nid_number,
    validate_adult_birth_date,
    validate_image_file,
)

class MemberProfile(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Officer Approval'),
        ('ACTIVE', 'Active / Approved'),
        ('REJECTED', 'Application Rejected'),
        ('INACTIVE', 'Inactive'),
    )
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile'
    )
    member_id = models.CharField(max_length=30, unique=True, blank=True)
    father_or_husband_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    nid_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="National ID (NID)", validators=[validate_nid_number])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE')
    date_of_birth = models.DateField(blank=True, null=True, validators=[validate_adult_birth_date])
    occupation = models.CharField(max_length=100, blank=True, null=True)
    present_address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    
    # Nominee Details
    nominee_name = models.CharField(max_length=100, blank=True, null=True)
    nominee_relation = models.CharField(max_length=50, blank=True, null=True)
    nominee_nid = models.CharField(max_length=50, blank=True, null=True, validators=[validate_nid_number])
    nominee_phone = models.CharField(max_length=20, blank=True, null=True, validators=[validate_bd_phone])

    # Document & Identification Photos
    member_photo = models.ImageField(upload_to='members/photos/', blank=True, null=True, verbose_name="Photo of Member", validators=[validate_image_file])
    nid_photo = models.ImageField(upload_to='members/nid/', blank=True, null=True, verbose_name="Photo of NID", validators=[validate_image_file])
    nominee_photo = models.ImageField(upload_to='members/nominees/', blank=True, null=True, verbose_name="Photo of Nominee", validators=[validate_image_file])

    # Management & Officer Assignment
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_members',
        limit_choices_to={'role': 'OFFICER'}
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    
    # KYC Review & Approval Tracking
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_members'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    joined_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.nid_number and self.nominee_nid and self.nid_number == self.nominee_nid:
            raise ValidationError({'nominee_nid': "Nominee NID cannot be the same as the member's NID."})
        user_phone = None
        try:
            if hasattr(self, 'user') and self.user and self.user.phone:
                user_phone = self.user.phone
        except Exception:
            user_phone = None
        if self.nominee_phone and user_phone and self.nominee_phone == user_phone:
            raise ValidationError({'nominee_phone': "Nominee mobile number cannot be the same as the member's mobile number."})

    def save(self, *args, **kwargs):
        if not self.member_id:
            # Auto-generate Member ID like TNS-MEM-0001
            last_member = MemberProfile.objects.exclude(member_id='').order_by('-id').first()
            next_id = (last_member.id + 1) if (last_member and last_member.id) else 1
            candidate_id = f"TNS-MEM-{next_id:04d}"
            counter = 1
            while MemberProfile.objects.filter(member_id=candidate_id).exists():
                candidate_id = f"TNS-MEM-{(next_id + counter):04d}"
                counter += 1
            self.member_id = candidate_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member_id} - {self.user.get_full_name() or self.user.username}"

    def get_status_badge(self):
        badges = {
            'ACTIVE': 'badge-success',
            'INACTIVE': 'badge-secondary',
            'PENDING': 'badge-warning',
            'REJECTED': 'badge-danger',
        }
        return badges.get(self.status, 'badge-info')
