import re
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from apps.accounts.models import CustomUser
from apps.core.validators import validate_bd_phone


def paginate(request, queryset, per_page=10):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def clean_phone_unique(phone, exclude_user_id=None):
    if not phone:
        return ''
    phone = validate_bd_phone(phone.strip())
    qs = CustomUser.objects.filter(phone=phone)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    if qs.exists():
        raise ValidationError("This mobile phone number is already registered to an existing account.")
    return phone


def clean_email_unique(email, exclude_user_id=None):
    if not email:
        return ''
    email = email.strip()
    qs = CustomUser.objects.filter(email__iexact=email)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    if qs.exists():
        raise ValidationError("This email address is already associated with an existing account.")
    return email


def validate_nominee_mismatch(phone, nominee_phone, nid, nominee_nid, add_error_func):
    if phone and nominee_phone:
        if re.sub(r'\D', '', phone) == re.sub(r'\D', '', nominee_phone):
            add_error_func('nominee_phone', "Nominee phone cannot be identical to the member's phone number.")
    if nid and nominee_nid:
        if re.sub(r'\D', '', nid) == re.sub(r'\D', '', nominee_nid):
            add_error_func('nominee_nid', "Nominee NID cannot be identical to the member's NID.")
