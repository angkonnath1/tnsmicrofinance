from django import forms
from apps.accounts.models import CustomUser
from .models import MemberProfile
from apps.core.validators import (
    validate_bd_phone,
    validate_nid_number,
    validate_adult_birth_date,
    validate_image_file,
)
from apps.core.utils import clean_phone_unique, clean_email_unique, validate_nominee_mismatch

DIGIT_ATTRS = {
    'inputmode': 'numeric',
    'pattern': '[0-9]*',
    'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
}


class MemberValidationMixin:
    def get_user_pk(self):
        if hasattr(self, 'instance') and self.instance:
            if hasattr(self.instance, 'user') and self.instance.user:
                return self.instance.user.pk
            if isinstance(self.instance, CustomUser):
                return self.instance.pk
        return None

    def clean_username(self):
        uname = (self.cleaned_data.get('username') or '').strip()
        if uname and CustomUser.objects.filter(username__iexact=uname).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return uname

    def clean_phone(self):
        return clean_phone_unique(self.cleaned_data.get('phone'), exclude_user_id=self.get_user_pk())

    def clean_email(self):
        return clean_email_unique(self.cleaned_data.get('email'), exclude_user_id=self.get_user_pk())

    def clean_nid_number(self):
        nid = (self.cleaned_data.get('nid_number') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
            qs = MemberProfile.objects.filter(nid_number=nid)
            if hasattr(self, 'instance') and self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A member with this National ID (NID) already exists.")
        return nid or None

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            validate_adult_birth_date(dob)
        return dob

    def clean_nominee_phone(self):
        phone = (self.cleaned_data.get('nominee_phone') or '').strip()
        return validate_bd_phone(phone) if phone else None

    def clean_nominee_nid(self):
        nid = (self.cleaned_data.get('nominee_nid') or '').strip()
        return validate_nid_number(nid) if nid else None

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def clean_member_photo(self):
        p = self.cleaned_data.get('member_photo')
        if p and hasattr(p, 'file'):
            validate_image_file(p)
        return p

    def clean_nid_photo(self):
        p = self.cleaned_data.get('nid_photo')
        if p and hasattr(p, 'file'):
            validate_image_file(p)
        return p

    def clean_nominee_photo(self):
        p = self.cleaned_data.get('nominee_photo')
        if p and hasattr(p, 'file'):
            validate_image_file(p)
        return p

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        cpwd = cleaned.get("confirm_password")
        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Passwords do not match. Please re-enter carefully.")

        validate_nominee_mismatch(
            cleaned.get('phone') or self.data.get('phone'),
            cleaned.get('nominee_phone') or self.data.get('nominee_phone'),
            cleaned.get('nid_number') or self.data.get('nid_number'),
            cleaned.get('nominee_nid') or self.data.get('nominee_nid'),
            self.add_error
        )
        return cleaned


class MemberSelfRegistrationForm(MemberValidationMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address (optional)'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number (e.g. 01712345678)', **DIGIT_ATTRS}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password (min. 6 characters)'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    present_address = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current living address'}))
    permanent_address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Village/Town, Post, Upazila, District'}))
    nid_number = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID (NID) Number', **DIGIT_ATTRS}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    occupation = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation (optional)'}))
    gender = forms.ChoiceField(choices=MemberProfile.GENDER_CHOICES, required=False, initial='MALE', widget=forms.Select(attrs={'class': 'form-select'}))

    member_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    nid_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    nominee_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    nominee_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee Full Name'}))
    nominee_relation = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relationship with Member'}))
    nominee_phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee Phone Number', **DIGIT_ATTRS}))
    nominee_nid = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee NID (optional)', **DIGIT_ATTRS}))

    class Meta:
        model = MemberProfile
        fields = [
            'nid_number', 'gender', 'date_of_birth', 'present_address', 'permanent_address', 'occupation',
            'member_photo', 'nid_photo',
            'nominee_name', 'nominee_relation', 'nominee_phone', 'nominee_nid', 'nominee_photo'
        ]


class MemberRegistrationForm(MemberValidationMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address (optional)'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', **DIGIT_ATTRS}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Initial Password'}), initial='123456')

    class Meta:
        model = MemberProfile
        fields = [
            'nid_number', 'gender', 'date_of_birth', 'father_or_husband_name', 'mother_name',
            'occupation', 'present_address', 'permanent_address',
            'member_photo', 'nid_photo',
            'nominee_name', 'nominee_relation', 'nominee_nid', 'nominee_phone', 'nominee_photo',
            'assigned_officer', 'status'
        ]
        widgets = {
            'nid_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID / Smart Card', **DIGIT_ATTRS}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'father_or_husband_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'present_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'permanent_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'member_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'nid_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'nominee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_nid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee NID', **DIGIT_ATTRS}),
            'nominee_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee Phone', **DIGIT_ATTRS}),
            'nominee_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class MemberProfileEditForm(MemberValidationMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', **DIGIT_ATTRS}))

    class Meta:
        model = MemberProfile
        fields = [
            'nid_number', 'gender', 'date_of_birth', 'father_or_husband_name', 'mother_name',
            'occupation', 'present_address', 'permanent_address',
            'member_photo', 'nid_photo',
            'nominee_name', 'nominee_relation', 'nominee_nid', 'nominee_phone', 'nominee_photo',
            'assigned_officer', 'status'
        ]
        widgets = {
            'nid_number': forms.TextInput(attrs={'class': 'form-control', **DIGIT_ATTRS}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'father_or_husband_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'present_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'permanent_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'member_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'nid_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'nominee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_nid': forms.TextInput(attrs={'class': 'form-control', **DIGIT_ATTRS}),
            'nominee_phone': forms.TextInput(attrs={'class': 'form-control', **DIGIT_ATTRS}),
            'nominee_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
