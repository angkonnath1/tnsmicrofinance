from django import forms
from decimal import Decimal
from .models import SavingsTransaction, SavingsAccount
from apps.members.models import MemberProfile
from apps.core.validators import validate_positive_amount

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
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trx ID / Bank Deposit Slip No / Note'})
    )

    class Meta:
        model = SavingsTransaction
        fields = ['amount', 'payment_method', 'reference_note']

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            validate_positive_amount(amount)
            if amount < Decimal('10.00'):
                raise forms.ValidationError("Minimum deposit amount is ৳10.00.")
            if amount > Decimal('1000000.00'):
                raise forms.ValidationError("Maximum single deposit limit is ৳1,000,000.00.")
        return amount

    def clean_reference_note(self):
        return (self.cleaned_data.get('reference_note') or '').strip()


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
        if amount is not None:
            validate_positive_amount(amount)
            if amount < Decimal('50.00'):
                raise forms.ValidationError("Minimum withdrawal amount is ৳50.00.")
            if self.account and amount > self.account.balance:
                raise forms.ValidationError(
                    f"Insufficient funds. Your current balance is ৳{self.account.balance}."
                )
        return amount

    def clean_reference_note(self):
        return (self.cleaned_data.get('reference_note') or '').strip()


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

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            validate_positive_amount(amount)
            if amount < Decimal('10.00'):
                raise forms.ValidationError("Minimum deposit amount is ৳10.00.")
        return amount

    def clean_member(self):
        member = self.cleaned_data.get('member')
        if member and member.status != 'ACTIVE':
            raise forms.ValidationError("Deposits can only be recorded for active members.")
        return member

    def clean_reference_note(self):
        return (self.cleaned_data.get('reference_note') or '').strip()


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

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            validate_positive_amount(amount)
            if amount < Decimal('50.00'):
                raise forms.ValidationError("Minimum withdrawal amount is ৳50.00.")
        return amount

    def clean_reference_note(self):
        return (self.cleaned_data.get('reference_note') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        amount = cleaned_data.get('amount')

        if member and amount is not None:
            if member.status != 'ACTIVE':
                self.add_error('member', "Withdrawals can only be processed for active members.")

            account = getattr(member, 'savings_account', None)
            if not account:
                self.add_error('member', f"Member {member.member_id} does not have a savings account.")
            elif account.balance < amount:
                self.add_error(
                    'amount',
                    f"Insufficient funds: Account balance is ৳{account.balance}, cannot withdraw ৳{amount}."
                )

        return cleaned_data
