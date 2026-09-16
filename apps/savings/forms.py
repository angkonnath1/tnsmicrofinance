from decimal import Decimal
from django import forms
from apps.members.models import MemberProfile
from .models import SavingsTransaction


class MemberDepositRequestForm(forms.ModelForm):
    amount = forms.DecimalField(
        min_value=Decimal('10.00'),
        max_value=Decimal('1000000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in BDT (e.g. 500)'})
    )
    payment_method = forms.ChoiceField(
        choices=SavingsTransaction.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reference_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trx ID / Bank Slip No / Note'})
    )

    class Meta:
        model = SavingsTransaction
        fields = ['amount', 'payment_method', 'reference_note']


class MemberWithdrawalRequestForm(forms.ModelForm):
    amount = forms.DecimalField(
        min_value=Decimal('50.00'),
        max_value=Decimal('1000000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount to withdraw in BDT'})
    )
    reference_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason / Note (optional)'})
    )

    class Meta:
        model = SavingsTransaction
        fields = ['amount', 'reference_note']

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and self.account and amount > self.account.balance:
            raise forms.ValidationError(f"Insufficient funds. Your current balance is ৳{self.account.balance}.")
        return amount


class StaffRecordDepositForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=MemberProfile.objects.filter(status='ACTIVE').select_related('user'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_member'}),
        empty_label="Select Member"
    )
    amount = forms.DecimalField(
        min_value=Decimal('10.00'),
        max_value=Decimal('5000000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in BDT'})
    )
    payment_method = forms.ChoiceField(
        choices=SavingsTransaction.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reference_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voucher No / Receipt Reference'})
    )


class StaffRecordWithdrawalForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=MemberProfile.objects.filter(status='ACTIVE').select_related('user'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_withdrawal_member'}),
        empty_label="Select Member"
    )
    amount = forms.DecimalField(
        min_value=Decimal('50.00'),
        max_value=Decimal('5000000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Withdrawal Amount'})
    )
    reference_note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voucher No / Withdrawal Slip'})
    )
