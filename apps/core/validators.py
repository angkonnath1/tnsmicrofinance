import os
import re
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Regex pattern for Bangladeshi and international mobile numbers
# Accepts: 01XXXXXXXXX, +8801XXXXXXXXX, 8801XXXXXXXXX, or standard E.164 numbers (10-15 digits)
BD_PHONE_REGEX = re.compile(r'^(?:\+?880|880|0)?1[3-9]\d{8}$')
INTL_PHONE_REGEX = re.compile(r'^\+?[1-9]\d{9,14}$')

def validate_bd_phone(value):
    """
    Validates mobile phone number format.
    Accepts Bangladeshi standard 11-digit numbers (013-019) with or without +88/88 prefix,
    or general international phone numbers. Strictly allows only numeric digits.
    """
    if not value:
        return value
    clean_val = re.sub(r'[\s\-\(\)\+]', '', str(value))
    if not clean_val.isdigit():
        raise ValidationError(
            _("Phone number must contain numbers only. Letters or characters are not allowed."),
            code='invalid_phone_characters'
        )
    if not (BD_PHONE_REGEX.match(clean_val) or INTL_PHONE_REGEX.match(clean_val) or re.match(r'^(?:88)?01[3-9]\d{8}$', clean_val)):
        raise ValidationError(
            _("Please enter a valid mobile number (e.g. 01712345678)."),
            code='invalid_phone'
        )
    return clean_val

def validate_nid_number(value):
    """
    Validates National ID (NID) format.
    Standard Bangladeshi NIDs are numeric: 10-digit Smart Card, 13-digit legacy, or 17-digit format.
    """
    if not value:
        return value
    clean_val = re.sub(r'[\s\-]', '', str(value))
    if not clean_val.isdigit():
        raise ValidationError(
            _("National ID (NID) must contain digits only."),
            code='invalid_nid_characters'
        )
    if len(clean_val) not in (10, 13, 17) and not (10 <= len(clean_val) <= 17):
        raise ValidationError(
            _("National ID (NID) must be between 10 and 17 digits (10-digit Smart NID, 13-digit, or 17-digit format)."),
            code='invalid_nid_length'
        )
    return clean_val

def validate_adult_birth_date(value):
    """
    Validates that the member's date of birth is in the past and they are at least 18 years old.
    """
    if not value:
        return value
    today = date.today()
    if value > today:
        raise ValidationError(
            _("Date of birth cannot be in the future."),
            code='future_birth_date'
        )
    # Calculate age
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError(
            _("Member must be at least 18 years old for cooperative membership."),
            code='underage_member'
        )
    if age > 120:
        raise ValidationError(
            _("Please enter a valid date of birth (maximum age is 120 years)."),
            code='invalid_age'
        )
    return value

def validate_image_file(file_obj):
    """
    Validates uploaded image file size (max 5MB) and allowed image extensions.
    """
    if not file_obj:
        return file_obj

    # Max 5 Megabytes
    max_size_bytes = 5 * 1024 * 1024
    if hasattr(file_obj, 'size') and file_obj.size > max_size_bytes:
        raise ValidationError(
            _("Uploaded image size must not exceed 5MB."),
            code='file_too_large'
        )

    # Validate file extension
    ext = os.path.splitext(file_obj.name)[1].lower() if hasattr(file_obj, 'name') else ''
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if ext and ext not in allowed_extensions:
        raise ValidationError(
            _("Unsupported file extension %(ext)s. Allowed formats: %(allowed)s"),
            params={'ext': ext, 'allowed': ', '.join(allowed_extensions)},
            code='invalid_image_extension'
        )
    return file_obj

def validate_positive_amount(value):
    """
    Validates that a financial amount is strictly positive (> 0.00).
    """
    if value is None:
        return value
    try:
        val = Decimal(str(value))
        if val <= Decimal('0.00'):
            raise ValidationError(
                _("Amount must be strictly greater than zero."),
                code='non_positive_amount'
            )
    except (ValueError, ArithmeticError):
        raise ValidationError(
            _("Please enter a valid numeric amount."),
            code='invalid_amount'
        )
    return value
