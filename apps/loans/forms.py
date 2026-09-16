from decimal import Decimal
from django import forms
from .models import LoanApplication, LoanScheme
from apps.members.models import MemberProfile
from apps.core.validators import validate_bd_phone, validate_nid_number


class MemberLoanApplicationForm(forms.ModelForm):
    loan_product = forms.ModelChoiceField(
        queryset=LoanScheme.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'loan_product_select'}),
        empty_label="-- Select Loan Scheme (Optional) --"
    )
    principal_amount = forms.DecimalField(
        min_value=Decimal('500.00'),
        max_value=Decimal('5000000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Loan Amount in BDT'})
    )
    duration_months = forms.IntegerField(
        min_value=1,
        max_value=60,
        initial=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration (Months)'})
    )
    installment_frequency = forms.ChoiceField(
        choices=LoanApplication.FREQUENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    purpose = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Small Grocery Store expansion, Agriculture'})
    )
    guarantor_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guarantor Full Name'})
    )
    guarantor_phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guarantor Phone Number'})
    )
    guarantor_nid = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guarantor NID / Smart Card'})
    )
    guarantor_relation = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brother, Neighbor, Business Partner'})
    )

    class Meta:
        model = LoanApplication
        fields = [
            'loan_product', 'principal_amount', 'duration_months', 'installment_frequency',
            'purpose', 'guarantor_name', 'guarantor_phone', 'guarantor_nid', 'guarantor_relation'
        ]

    def __init__(self, *args, applicant_member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.applicant_member = applicant_member

    def clean_guarantor_phone(self):
        phone = (self.cleaned_data.get('guarantor_phone') or '').strip()
        return validate_bd_phone(phone) if phone else ''

    def clean_guarantor_nid(self):
        nid = (self.cleaned_data.get('guarantor_nid') or '').strip()
        return validate_nid_number(nid) if nid else ''

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('loan_product')
        amount = cleaned.get('principal_amount')

        if product and amount is not None:
            if amount < product.min_amount:
                self.add_error('principal_amount', f"Scheme '{product.name}' requires minimum ৳{product.min_amount}.")
            elif amount > product.max_amount:
                self.add_error('principal_amount', f"Scheme '{product.name}' allows maximum ৳{product.max_amount}.")

        member = self.applicant_member
        g_phone = cleaned.get('guarantor_phone')
        g_nid = cleaned.get('guarantor_nid')

        if member:
            if hasattr(member, 'user') and member.user and member.user.phone and g_phone == member.user.phone:
                self.add_error('guarantor_phone', "Guarantor phone cannot be the applicant's own phone.")
            if member.nid_number and g_nid and g_nid == member.nid_number:
                self.add_error('guarantor_nid', "Guarantor NID cannot be the applicant's own NID.")
            if LoanApplication.objects.filter(member=member, status='DEFAULTED').exists():
                raise forms.ValidationError("Member has an unresolved defaulted loan and is not eligible for a new loan.")

        return cleaned


class StaffLoanApplicationForm(MemberLoanApplicationForm):
    member = forms.ModelChoiceField(
        queryset=MemberProfile.objects.filter(status='ACTIVE').select_related('user'),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="-- Select Member --"
    )

    class Meta(MemberLoanApplicationForm.Meta):
        fields = ['member'] + MemberLoanApplicationForm.Meta.fields

    def clean(self):
        member = self.cleaned_data.get('member')
        if member:
            self.applicant_member = member
        return super().clean()


class LoanSchemeForm(forms.ModelForm):
    class Meta:
        model = LoanScheme
        fields = ['name', 'min_amount', 'max_amount', 'interest_rate_percent', 'duration_months', 'installment_frequency', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'interest_rate_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'duration_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'installment_frequency': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
