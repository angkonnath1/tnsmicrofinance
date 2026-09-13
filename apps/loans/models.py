from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from apps.members.models import MemberProfile

class LoanScheme(models.Model):
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('5000.00'))
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('500000.00'))
    interest_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'), help_text="Flat interest rate percentage")
    duration_months = models.IntegerField(default=12, help_text="Duration in months")
    installment_frequency = models.CharField(
        max_length=10,
        choices=(('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')),
        default='MONTHLY'
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.interest_rate_percent}%)"

class LoanApplication(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('DISBURSED', 'Disbursed / Active'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Fully Repaid'),
        ('DEFAULTED', 'Overdue / Defaulted'),
    )
    FREQUENCY_CHOICES = (
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    )

    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='loans'
    )
    loan_product = models.ForeignKey(
        LoanScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loans'
    )
    loan_id = models.CharField(max_length=30, unique=True, blank=True)
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    duration_months = models.IntegerField(default=12)
    installment_frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='MONTHLY')
    
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    purpose = models.CharField(max_length=255)
    guarantor_name = models.CharField(max_length=100)
    guarantor_phone = models.CharField(max_length=20)
    guarantor_nid = models.CharField(max_length=50, blank=True, null=True)
    guarantor_relation = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    applied_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-applied_at']

    def save(self, *args, **kwargs):
        # Auto-calculate totals
        principal = Decimal(str(self.principal_amount))
        rate = Decimal(str(self.interest_rate))
        months = Decimal(str(self.duration_months))

        # Flat rate formula: (Principal * Rate% * (Months / 12))
        self.total_interest = round(principal * (rate / Decimal('100.0')) * (months / Decimal('12.0')), 2)
        self.total_payable = principal + self.total_interest

        if not self.loan_id:
            last_loan = LoanApplication.objects.exclude(loan_id='').order_by('-id').first()
            next_id = (last_loan.id + 1) if (last_loan and last_loan.id) else 1
            self.loan_id = f"TNS-LN-{next_id:04d}"

        super().save(*args, **kwargs)

    def generate_installments(self):
        """Generates installments when a loan is disbursed."""
        self.installments.all().delete()

        num_installments = (self.duration_months * 4) if self.installment_frequency == 'WEEKLY' else self.duration_months
        if num_installments <= 0:
            num_installments = 1

        installment_amount = round(self.total_payable / Decimal(str(num_installments)), 2)
        principal_part = round(self.principal_amount / Decimal(str(num_installments)), 2)
        interest_part = installment_amount - principal_part

        start_date = timezone.now().date()
        installments = []

        for i in range(1, num_installments + 1):
            if self.installment_frequency == 'WEEKLY':
                due_date = start_date + timedelta(weeks=i)
            else:
                # Add 30 days per month
                due_date = start_date + timedelta(days=30 * i)

            # Adjust last installment for rounding discrepancies
            if i == num_installments:
                already_allocated = installment_amount * Decimal(str(num_installments - 1))
                installment_amount = self.total_payable - already_allocated
                principal_part = self.principal_amount - (principal_part * Decimal(str(num_installments - 1)))
                interest_part = installment_amount - principal_part

            installments.append(
                LoanInstallment(
                    loan=self,
                    installment_number=i,
                    due_date=due_date,
                    principal_amount=principal_part,
                    interest_amount=interest_part,
                    total_amount=installment_amount,
                    status='PENDING'
                )
            )

        LoanInstallment.objects.bulk_create(installments)

    @property
    def remaining_balance(self):
        return max(Decimal('0.00'), self.total_payable - self.total_paid)

    @property
    def progress_percentage(self):
        if self.total_payable > 0:
            return min(100, int((self.total_paid / self.total_payable) * 100))
        return 0

    def get_status_badge(self):
        badges = {
            'PENDING': 'badge-warning',
            'APPROVED': 'badge-info',
            'DISBURSED': 'badge-primary',
            'COMPLETED': 'badge-success',
            'REJECTED': 'badge-danger',
            'DEFAULTED': 'badge-danger',
        }
        return badges.get(self.status, 'badge-secondary')

    def __str__(self):
        return f"{self.loan_id} - {self.member.member_id} ({self.principal_amount} BDT - {self.status})"

class LoanInstallment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    )

    loan = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='installments'
    )
    installment_number = models.IntegerField()
    due_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    PAYMENT_METHOD_CHOICES = (
        ('SAVINGS', 'Savings Account Balance'),
        ('SSLCOMMERZ', 'SSLCOMMERZ Online Gateway'),
        ('CASH', 'Cash Payment'),
        ('BKASH', 'bKash Mobile Banking'),
        ('NAGAD', 'Nagad Mobile Banking'),
        ('BANK', 'Bank Transfer'),
    )

    paid_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_installments'
    )

    class Meta:
        ordering = ['installment_number']

    def mark_as_paid(self, collector=None, payment_amount=None, method='CASH', reference=None):
        amount = Decimal(str(payment_amount)) if payment_amount else self.total_amount
        self.paid_amount = amount
        self.status = 'PAID'
        self.paid_date = timezone.now().date()
        self.payment_method = method
        self.payment_reference = reference
        self.collected_by = collector
        self.save()

        # Update parent loan total_paid
        loan = self.loan
        loan.total_paid += amount
        if loan.total_paid >= loan.total_payable:
            loan.status = 'COMPLETED'
        loan.save()

    def get_status_badge(self):
        badges = {
            'PAID': 'badge-success',
            'PENDING': 'badge-warning',
            'OVERDUE': 'badge-danger',
        }
        return badges.get(self.status, 'badge-secondary')

    def __str__(self):
        return f"Installment #{self.installment_number} for {self.loan.loan_id} ({self.total_amount} BDT - {self.status})"

class SSLLoanPaymentSession(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Payment'),
        ('VALID', 'Payment Validated / Success'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled'),
    )
    
    tran_id = models.CharField(max_length=64, unique=True)
    val_id = models.CharField(max_length=64, blank=True, null=True)
    installment = models.ForeignKey(LoanInstallment, on_delete=models.CASCADE, related_name='ssl_sessions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    bank_tran_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SSL Loan Session {self.tran_id} (Inst #{self.installment.installment_number} - {self.amount} BDT - {self.status})"
