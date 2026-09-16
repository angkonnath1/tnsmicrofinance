from django import forms
from decimal import Decimal
from .models import LoanApplication, LoanScheme, LoanInstallment
from apps.members.models import MemberProfile
from apps.core.validators import validate_bd_phone, validate_nid_number, validate_positive_amount

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

    def clean_principal_amount(self):
        amount = self.cleaned_data.get('principal_amount')
        if amount is not None:
            validate_positive_amount(amount)
        return amount

    def clean_guarantor_phone(self):
        phone = (self.cleaned_data.get('guarantor_phone') or '').strip()
        if phone:
            phone = validate_bd_phone(phone)
        return phone

    def clean_guarantor_nid(self):
        nid = (self.cleaned_data.get('guarantor_nid') or '').strip()
        if nid:
            nid = validate_nid_number(nid)
        return nid

    def clean(self):
        cleaned_data = super().clean()
        loan_product = cleaned_data.get('loan_product')
        principal_amount = cleaned_data.get('principal_amount')

        if loan_product and principal_amount is not None:
            if principal_amount < loan_product.min_amount:
                self.add_error(
                    'principal_amount',
                    f"Selected scheme '{loan_product.name}' requires a minimum amount of ৳{loan_product.min_amount}."
                )
            elif principal_amount > loan_product.max_amount:
                self.add_error(
                    'principal_amount',
                    f"Selected scheme '{loan_product.name}' allows a maximum amount of ৳{loan_product.max_amount}."
                )

        member = self.applicant_member
        guarantor_phone = cleaned_data.get('guarantor_phone')
        guarantor_nid = cleaned_data.get('guarantor_nid')

        if member:
            if hasattr(member, 'user') and member.user and member.user.phone:
                if guarantor_phone and guarantor_phone == member.user.phone:
                    self.add_error('guarantor_phone', "Guarantor phone cannot be the applicant's own phone number.")
            if member.nid_number and guarantor_nid:
                if guarantor_nid == member.nid_number:
                    self.add_error('guarantor_nid', "Guarantor NID cannot be the applicant's own NID.")

            # Check for defaulted loans
            if LoanApplication.objects.filter(member=member, status='DEFAULTED').exists():
                raise forms.ValidationError("Member has an unresolved defaulted loan and is not eligible for a new loan.")

        return cleaned_data


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
            if member.status != 'ACTIVE':
                self.add_error('member', "Loans can only be created for active members.")
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

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        rate = cleaned_data.get('interest_rate_percent')
        duration = cleaned_data.get('duration_months')

        if min_amount is not None and min_amount <= Decimal('0.00'):
            self.add_error('min_amount', "Minimum amount must be greater than zero.")

        if min_amount is not None and max_amount is not None and max_amount < min_amount:
            self.add_error('max_amount', "Maximum amount cannot be less than minimum amount.")

        if rate is not None and (rate < Decimal('0.00') or rate > Decimal('100.00')):
            self.add_error('interest_rate_percent', "Interest rate must be between 0% and 100%.")

        if duration is not None and (duration < 1 or duration > 120):
            self.add_error('duration_months', "Duration must be between 1 and 120 months.")

        return cleaned_data
