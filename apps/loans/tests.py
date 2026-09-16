from django.test import TestCase
from decimal import Decimal
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile
from apps.loans.models import LoanApplication

class LoansTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='loan_user', role='MEMBER', password='password123')
        self.profile = MemberProfile.objects.create(user=self.user)
        self.loan = LoanApplication.objects.create(
            member=self.profile,
            principal_amount=Decimal('12000.00'),
            interest_rate=Decimal('10.00'),
            duration_months=12,
            installment_frequency='MONTHLY',
            purpose='Small business',
            guarantor_name='Guarantor X',
            guarantor_phone='01700000000',
            status='DISBURSED'
        )

    def test_loan_calculations_and_schedule(self):
        # 12000 principal + 10% annual interest = 1200 interest -> 13200 total payable
        self.assertEqual(self.loan.total_interest, Decimal('1200.00'))
        self.assertEqual(self.loan.total_payable, Decimal('13200.00'))

        self.loan.generate_installments()
        self.assertEqual(self.loan.installments.count(), 12)

        first_inst = self.loan.installments.first()
        first_inst.mark_as_paid()
        self.loan.refresh_from_db()

        self.assertEqual(self.loan.total_paid, first_inst.total_amount)
        self.assertEqual(self.loan.remaining_balance, self.loan.total_payable - first_inst.total_amount)
