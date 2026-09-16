from django.test import TestCase
from decimal import Decimal
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount

class SavingsTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test_member', role='MEMBER', password='password123')
        self.profile = MemberProfile.objects.create(user=self.user)
        self.account = SavingsAccount.objects.create(member=self.profile, account_number='SAV-TEST-01', balance=Decimal('1000.00'))

    def test_deposit(self):
        self.account.deposit(Decimal('500.00'))
        self.assertEqual(self.account.balance, Decimal('1500.00'))

    def test_withdrawal(self):
        success = self.account.withdraw(Decimal('300.00'))
        self.assertTrue(success)
        self.assertEqual(self.account.balance, Decimal('700.00'))

    def test_insufficient_withdrawal(self):
        success = self.account.withdraw(Decimal('2000.00'))
        self.assertFalse(success)
        self.assertEqual(self.account.balance, Decimal('1000.00'))
