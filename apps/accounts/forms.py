from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from .models import CustomUser
from apps.core.validators import validate_bd_phone, validate_image_file

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email', 'id': 'username_input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'id': 'password_input'})
    )

    def clean_username(self):
        return self.cleaned_data.get('username', '').strip()

    def clean_password(self):
        return self.cleaned_data.get('password', '').strip()

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user_obj = CustomUser.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
            if user_obj and user_obj.check_password(password):
                # Check member KYC review status if member
                if hasattr(user_obj, 'member_profile'):
                    profile = user_obj.member_profile
                    if profile.status == 'PENDING' or not user_obj.is_active:
                        raise forms.ValidationError(
                            f"⏳ Account ({profile.member_id}) is pending KYC verification and officer approval. You will be able to log in as soon as an officer approves your registration."
                        )
                    elif profile.status == 'REJECTED':
                        reason_msg = f" Reason: {profile.rejection_reason}" if profile.rejection_reason else ""
                        raise forms.ValidationError(
                            f"❌ Your membership application was rejected by the officer.{reason_msg} Please contact Touch & Solve office."
                        )
                    elif profile.status == 'INACTIVE' or not user_obj.is_active:
                        raise forms.ValidationError("This member account has been deactivated. Please contact your field officer.")
                elif not user_obj.is_active:
                    raise forms.ValidationError("This account has been deactivated.")

                cleaned_data['user'] = user_obj
            else:
                raise forms.ValidationError("Invalid username/email or password.")
        return cleaned_data

class OfficerCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), min_length=6)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
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
                raise forms.ValidationError("This mobile phone number is already registered to another user.")
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email:
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'OFFICER'
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
            query = CustomUser.objects.filter(phone=phone)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError("This phone number is already used by another account.")
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email:
            query = CustomUser.objects.filter(email__iexact=email)
            if self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError("This email address is already in use by another account.")
        return email

    def clean_profile_picture(self):
        photo = self.cleaned_data.get('profile_picture')
        if photo:
            validate_image_file(photo)
        return photo
