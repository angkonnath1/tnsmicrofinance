import re
from django import forms
from apps.accounts.models import CustomUser
from .models import MemberProfile
from apps.core.validators import (
    validate_bd_phone,
    validate_nid_number,
    validate_adult_birth_date,
    validate_image_file,
)

class MemberSelfRegistrationForm(forms.ModelForm):
    # Personal & Account
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address (optional)'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number (e.g. 01712345678)'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password (min. 6 characters)'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    # Address & NID
    present_address = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current living address'}))
    permanent_address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Village/Town, Post, Upazila, District'}))
    nid_number = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID (NID) Number'}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    occupation = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation (optional)'}))
    gender = forms.ChoiceField(choices=MemberProfile.GENDER_CHOICES, required=False, initial='MALE', widget=forms.Select(attrs={'class': 'form-select'}))

    # Photos
    member_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    nid_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    nominee_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # Nominee Details
    nominee_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee Full Name'}))
    nominee_relation = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relationship with Member'}))
    nominee_phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee Phone Number'}))
    nominee_nid = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nominee NID (optional)'}))

    class Meta:
        model = MemberProfile
        fields = [
            'nid_number', 'gender', 'date_of_birth', 'present_address', 'permanent_address', 'occupation',
            'member_photo', 'nid_photo',
            'nominee_name', 'nominee_relation', 'nominee_phone', 'nominee_nid', 'nominee_photo'
        ]

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
            if CustomUser.objects.filter(phone=phone).exists():
                raise forms.ValidationError("This mobile phone number is already registered to an existing account.")
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email:
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError("This email address is already associated with an existing account.")
        return email

    def clean_nid_number(self):
        nid = (self.cleaned_data.get('nid_number') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
            if MemberProfile.objects.filter(nid_number=nid).exists():
                raise forms.ValidationError("A member with this National ID (NID) is already registered.")
        return nid or None

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            validate_adult_birth_date(dob)
        return dob

    def clean_nominee_phone(self):
        phone = (self.cleaned_data.get('nominee_phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
        return phone or None

    def clean_nominee_nid(self):
        nid = (self.cleaned_data.get('nominee_nid') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
        return nid or None

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def clean_member_photo(self):
        photo = self.cleaned_data.get('member_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean_nid_photo(self):
        photo = self.cleaned_data.get('nid_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean_nominee_photo(self):
        photo = self.cleaned_data.get('nominee_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match. Please re-enter carefully.")

        phone = (cleaned_data.get('phone') or self.data.get('phone') or '').strip()
        nominee_phone = (cleaned_data.get('nominee_phone') or self.data.get('nominee_phone') or '').strip()
        if phone and nominee_phone:
            p_clean = re.sub(r'[\s\-\(\)]', '', phone)
            np_clean = re.sub(r'[\s\-\(\)]', '', nominee_phone)
            if p_clean == np_clean:
                self.add_error('nominee_phone', "Nominee phone cannot be identical to the member's phone number.")

        nid = (cleaned_data.get('nid_number') or self.data.get('nid_number') or '').strip()
        nominee_nid = (cleaned_data.get('nominee_nid') or self.data.get('nominee_nid') or '').strip()
        if nid and nominee_nid:
            n_clean = re.sub(r'[\s\-]', '', nid)
            nn_clean = re.sub(r'[\s\-]', '', nominee_nid)
            if n_clean == nn_clean:
                self.add_error('nominee_nid', "Nominee NID cannot be identical to the member's NID.")

        return cleaned_data


class MemberRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address (optional)'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))
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
            'nid_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID / Smart Card'}),
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
            'nominee_nid': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
            if CustomUser.objects.filter(phone=phone).exists():
                raise forms.ValidationError("This phone number is already registered to another user.")
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email:
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError("This email is already in use by another user.")
        return email

    def clean_nid_number(self):
        nid = (self.cleaned_data.get('nid_number') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
            if MemberProfile.objects.filter(nid_number=nid).exists():
                raise forms.ValidationError("A member with this National ID (NID) already exists.")
        return nid or None

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            validate_adult_birth_date(dob)
        return dob

    def clean_nominee_phone(self):
        phone = (self.cleaned_data.get('nominee_phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
        return phone or None

    def clean_nominee_nid(self):
        nid = (self.cleaned_data.get('nominee_nid') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
        return nid or None

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def clean_member_photo(self):
        photo = self.cleaned_data.get('member_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean_nid_photo(self):
        photo = self.cleaned_data.get('nid_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean_nominee_photo(self):
        photo = self.cleaned_data.get('nominee_photo')
        if photo:
            validate_image_file(photo)
        return photo

    def clean(self):
        cleaned_data = super().clean()
        phone = (cleaned_data.get('phone') or self.data.get('phone') or '').strip()
        nominee_phone = (cleaned_data.get('nominee_phone') or self.data.get('nominee_phone') or '').strip()
        if phone and nominee_phone:
            p_clean = re.sub(r'[\s\-\(\)]', '', phone)
            np_clean = re.sub(r'[\s\-\(\)]', '', nominee_phone)
            if p_clean == np_clean:
                self.add_error('nominee_phone', "Nominee phone cannot be identical to the member's phone.")

        nid = (cleaned_data.get('nid_number') or self.data.get('nid_number') or '').strip()
        nominee_nid = (cleaned_data.get('nominee_nid') or self.data.get('nominee_nid') or '').strip()
        if nid and nominee_nid:
            n_clean = re.sub(r'[\s\-]', '', nid)
            nn_clean = re.sub(r'[\s\-]', '', nominee_nid)
            if n_clean == nn_clean:
                self.add_error('nominee_nid', "Nominee NID cannot be identical to the member's NID.")

        return cleaned_data


class MemberProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

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
            'nid_number': forms.TextInput(attrs={'class': 'form-control'}),
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
            'nominee_nid': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'nominee_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
            query = CustomUser.objects.filter(phone=phone)
            if self.instance and hasattr(self.instance, 'user') and self.instance.user:
                query = query.exclude(pk=self.instance.user.pk)
            if query.exists():
                raise forms.ValidationError("This phone number is already registered to another user.")
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email:
            query = CustomUser.objects.filter(email__iexact=email)
            if self.instance and hasattr(self.instance, 'user') and self.instance.user:
                query = query.exclude(pk=self.instance.user.pk)
            if query.exists():
                raise forms.ValidationError("This email is already in use by another user.")
        return email

    def clean_nid_number(self):
        nid = (self.cleaned_data.get('nid_number') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
            query = MemberProfile.objects.filter(nid_number=nid)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError("Another member with this NID already exists.")
        return nid or None

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            validate_adult_birth_date(dob)
        return dob

    def clean_nominee_phone(self):
        phone = (self.cleaned_data.get('nominee_phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
        return phone or None

    def clean_nominee_nid(self):
        nid = (self.cleaned_data.get('nominee_nid') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
        return nid or None

    def clean_member_photo(self):
        photo = self.cleaned_data.get('member_photo')
        if photo and hasattr(photo, 'file'):
            validate_image_file(photo)
        return photo

    def clean_nid_photo(self):
        photo = self.cleaned_data.get('nid_photo')
        if photo and hasattr(photo, 'file'):
            validate_image_file(photo)
        return photo

    def clean_nominee_photo(self):
        photo = self.cleaned_data.get('nominee_photo')
        if photo and hasattr(photo, 'file'):
            validate_image_file(photo)
        return photo

    def clean(self):
        cleaned_data = super().clean()
        phone = (cleaned_data.get('phone') or self.data.get('phone') or '').strip()
        nominee_phone = (cleaned_data.get('nominee_phone') or self.data.get('nominee_phone') or '').strip()
        if phone and nominee_phone:
            p_clean = re.sub(r'[\s\-\(\)]', '', phone)
            np_clean = re.sub(r'[\s\-\(\)]', '', nominee_phone)
            if p_clean == np_clean:
                self.add_error('nominee_phone', "Nominee phone cannot be identical to the member's phone.")

        nid = (cleaned_data.get('nid_number') or self.data.get('nid_number') or '').strip()
        nominee_nid = (cleaned_data.get('nominee_nid') or self.data.get('nominee_nid') or '').strip()
        if nid and nominee_nid:
            n_clean = re.sub(r'[\s\-]', '', nid)
            nn_clean = re.sub(r'[\s\-]', '', nominee_nid)
            if n_clean == nn_clean:
                self.add_error('nominee_nid', "Nominee NID cannot be identical to the member's NID.")

        return cleaned_data
