from django import forms
from django.db.models import Q
from .models import CustomUser
from apps.core.validators import validate_image_file
from apps.core.utils import clean_phone_unique, clean_email_unique

DIGIT_ATTRS = {
    'inputmode': 'numeric',
    'pattern': '[0-9]*',
    'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
}


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email', 'id': 'username_input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'id': 'password_input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = (cleaned_data.get('username') or '').strip()
        password = (cleaned_data.get('password') or '').strip()

        if username and password:
            user_obj = CustomUser.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
            if user_obj and user_obj.check_password(password):
                if hasattr(user_obj, 'member_profile'):
                    profile = user_obj.member_profile
                    if profile.status == 'PENDING' or not user_obj.is_active:
                        raise forms.ValidationError(
                            f"Account ({profile.member_id}) is pending KYC verification and officer approval."
                        )
                    elif profile.status == 'REJECTED':
                        reason = f" Reason: {profile.rejection_reason}" if profile.rejection_reason else ""
                        raise forms.ValidationError(f"Your membership application was rejected.{reason}")
                    elif profile.status == 'INACTIVE' or not user_obj.is_active:
                        raise forms.ValidationError("This member account has been deactivated.")
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
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number (e.g. 01712345678)', **DIGIT_ATTRS}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_username(self):
        uname = (self.cleaned_data.get('username') or '').strip()
        if CustomUser.objects.filter(username__iexact=uname).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return uname

    def clean_phone(self):
        return clean_phone_unique(self.cleaned_data.get('phone'))

    def clean_email(self):
        return clean_email_unique(self.cleaned_data.get('email'))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
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
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number', **DIGIT_ATTRS}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        return clean_phone_unique(self.cleaned_data.get('phone'), exclude_user_id=self.instance.pk)

    def clean_email(self):
        return clean_email_unique(self.cleaned_data.get('email'), exclude_user_id=self.instance.pk)

    def clean_profile_picture(self):
        photo = self.cleaned_data.get('profile_picture')
        if photo and hasattr(photo, 'file'):
            validate_image_file(photo)
        return photo
