from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.members.models import MemberProfile

class SavingsAccount(models.Model):
    member = models.OneToOneField(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='savings_account'
    )
    account_number = models.CharField(max_length=40, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_number} ({self.member.user.get_full_name()}) - Balance: {self.balance}"

    def deposit(self, amount):
        amount = Decimal(str(amount))
        if amount > Decimal('0.00'):
            self.balance += amount
            self.save(update_fields=['balance', 'updated_at'])
            return True
        return False

    def withdraw(self, amount):
        amount = Decimal(str(amount))
        if Decimal('0.00') < amount <= self.balance:
            self.balance -= amount
            self.save(update_fields=['balance', 'updated_at'])
            return True
        return False

class SavingsTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('BKASH', 'bKash'),
        ('NAGAD', 'Nagad'),
        ('ROCKET', 'Rocket'),
        ('BANK', 'Bank Transfer'),
        ('SSLCOMMERZ', 'SSLCOMMERZ Gateway'),
        ('SAVINGS', 'Savings Account Balance'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved / Completed'),
        ('REJECTED', 'Rejected'),
    )

    account = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPE_CHOICES, default='DEPOSIT')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    reference_note = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='APPROVED')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_savings_transactions'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_savings_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} - {self.account.member.member_id} ({self.status})"

    def get_status_badge(self):
        badges = {
            'APPROVED': 'badge-success',
            'PENDING': 'badge-warning',
            'REJECTED': 'badge-danger',
        }
        return badges.get(self.status, 'badge-secondary')

class SSLPaymentSession(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('VALID', 'Payment Validated / Success'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled'),
    )
    
    tran_id = models.CharField(max_length=64, unique=True)
    val_id = models.CharField(max_length=64, blank=True, null=True)
    account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='ssl_sessions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    bank_tran_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SSL Session {self.tran_id} ({self.amount} BDT - {self.status})"
