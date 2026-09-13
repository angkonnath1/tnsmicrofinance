import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tns_microfinance.settings')
django.setup()

from django.utils import timezone
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.loans.models import LoanScheme, LoanApplication, LoanInstallment
from apps.notifications.models import Notification

def seed():
    print("[*] Seeding Touch and Solve Micro Finance Database...")

    # 1. Create Admin
    admin_user, created = CustomUser.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@touchandsolve.com',
            'first_name': 'Touch & Solve',
            'last_name': 'Admin',
            'role': 'ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'phone': '01711000000',
        }
    )
    admin_user.set_password('admin123')
    admin_user.save()
    print("  - Admin User: admin (password: admin123)")

    # 2. Create Officers
    officer1, _ = CustomUser.objects.get_or_create(
        username='officer1',
        defaults={
            'email': 'officer1@touchandsolve.com',
            'first_name': 'Tareq',
            'last_name': 'Hasan',
            'role': 'OFFICER',
            'phone': '01811000001',
            'is_staff': True,
        }
    )
    officer1.set_password('123456')
    officer1.save()

    officer2, _ = CustomUser.objects.get_or_create(
        username='officer2',
        defaults={
            'email': 'officer2@touchandsolve.com',
            'first_name': 'Salma',
            'last_name': 'Khatun',
            'role': 'OFFICER',
            'phone': '01811000002',
            'is_staff': True,
        }
    )
    officer2.set_password('123456')
    officer2.save()
    print("  - Officers: officer1, officer2 (password: 123456)")

    # 3. Create Standard Loan Schemes
    scheme1, _ = LoanScheme.objects.get_or_create(
        name="Micro Enterprise Loan",
        defaults={
            'min_amount': Decimal('10000.00'),
            'max_amount': Decimal('200000.00'),
            'interest_rate_percent': Decimal('10.00'),
            'duration_months': 12,
            'installment_frequency': 'MONTHLY',
            'description': 'Designed for small business development and retail store inventory.',
            'is_active': True,
        }
    )

    scheme2, _ = LoanScheme.objects.get_or_create(
        name="Weekly Small Trade Loan",
        defaults={
            'min_amount': Decimal('5000.00'),
            'max_amount': Decimal('50000.00'),
            'interest_rate_percent': Decimal('8.00'),
            'duration_months': 6,
            'installment_frequency': 'WEEKLY',
            'description': 'Weekly repayment loan for daily vegetable, grocery and trade vendors.',
            'is_active': True,
        }
    )

    scheme3, _ = LoanScheme.objects.get_or_create(
        name="Emergency Assistance Loan",
        defaults={
            'min_amount': Decimal('5000.00'),
            'max_amount': Decimal('30000.00'),
            'interest_rate_percent': Decimal('5.00'),
            'duration_months': 3,
            'installment_frequency': 'MONTHLY',
            'description': 'Low interest short-term emergency funds for members in need.',
            'is_active': True,
        }
    )
    print("  - Loan Schemes created (Micro Enterprise, Weekly Trade, Emergency)")

    # 4. Create Member 1 (Rahim Uddin) - Active Loan & Active Savings
    user_mem1, _ = CustomUser.objects.get_or_create(
        username='rahim',
        defaults={
            'first_name': 'Rahim',
            'last_name': 'Uddin',
            'email': 'rahim@gmail.com',
            'phone': '01712345671',
            'role': 'MEMBER',
        }
    )
    user_mem1.set_password('123456')
    user_mem1.save()

    mem1, _ = MemberProfile.objects.get_or_create(
        user=user_mem1,
        defaults={
            'member_id': 'TNS-MEM-0001',
            'nid_number': '199026920110001',
            'gender': 'MALE',
            'date_of_birth': date(1990, 5, 12),
            'father_or_husband_name': 'Abdul Jabbar',
            'mother_name': 'Amena Begum',
            'occupation': 'Grocery Shop Owner',
            'present_address': 'House 12, Road 4, Mirpur-10, Dhaka',
            'permanent_address': 'Vill: Sonapur, Thana: Begumganj, Dist: Noakhali',
            'nominee_name': 'Rashida Sultana',
            'nominee_relation': 'Wife',
            'nominee_phone': '01712345672',
            'nominee_nid': '199326920110002',
            'assigned_officer': officer1,
            'status': 'ACTIVE',
        }
    )

    sav1, _ = SavingsAccount.objects.get_or_create(
        member=mem1,
        defaults={
            'account_number': 'SAV-0001',
            'balance': Decimal('0.00'),
        }
    )
    sav1.balance = Decimal('0.00')
    sav1.save()

    # 5. Create Member 2 (Fatema Begum)
    user_mem2, _ = CustomUser.objects.get_or_create(
        username='fatema',
        defaults={
            'first_name': 'Fatema',
            'last_name': 'Begum',
            'email': 'fatema@gmail.com',
            'phone': '01712345673',
            'role': 'MEMBER',
        }
    )
    user_mem2.set_password('123456')
    user_mem2.save()

    mem2, _ = MemberProfile.objects.get_or_create(
        user=user_mem2,
        defaults={
            'member_id': 'TNS-MEM-0002',
            'nid_number': '199226920110003',
            'gender': 'FEMALE',
            'date_of_birth': date(1992, 8, 20),
            'father_or_husband_name': 'Anwar Hossain',
            'mother_name': 'Sufia Khatun',
            'occupation': 'Boutique Tailor',
            'present_address': 'Sector 7, Uttara, Dhaka',
            'permanent_address': 'Vill: Rampur, Dist: Comilla',
            'nominee_name': 'Anwar Hossain',
            'nominee_relation': 'Husband',
            'nominee_phone': '01712345674',
            'assigned_officer': officer2,
            'status': 'ACTIVE',
        }
    )

    sav2, _ = SavingsAccount.objects.get_or_create(
        member=mem2,
        defaults={
            'account_number': 'SAV-0002',
            'balance': Decimal('0.00'),
        }
    )
    sav2.balance = Decimal('0.00')
    sav2.save()

    # 6. Create Member 3 (Kamal Hossain)
    user_mem3, _ = CustomUser.objects.get_or_create(
        username='kamal',
        defaults={
            'first_name': 'Kamal',
            'last_name': 'Hossain',
            'email': 'kamal@gmail.com',
            'phone': '01712345675',
            'role': 'MEMBER',
        }
    )
    user_mem3.set_password('123456')
    user_mem3.save()

    mem3, _ = MemberProfile.objects.get_or_create(
        user=user_mem3,
        defaults={
            'member_id': 'TNS-MEM-0003',
            'nid_number': '199526920110005',
            'gender': 'MALE',
            'date_of_birth': date(1995, 3, 15),
            'father_or_husband_name': 'Mofizur Rahman',
            'mother_name': 'Khaleda Begum',
            'occupation': 'Poultry Farmer',
            'present_address': 'Savar, Dhaka',
            'permanent_address': 'Savar, Dhaka',
            'nominee_name': 'Shirin Akter',
            'nominee_relation': 'Sister',
            'nominee_phone': '01712345676',
            'assigned_officer': officer1,
            'status': 'ACTIVE',
        }
    )

    sav3, _ = SavingsAccount.objects.get_or_create(
        member=mem3,
        defaults={
            'account_number': 'SAV-0003',
            'balance': Decimal('0.00'),
        }
    )
    sav3.balance = Decimal('0.00')
    sav3.save()

    # 7. Create Demo Welcome Notification
    Notification.objects.get_or_create(
        user=admin_user,
        title="Welcome to Touch & Solve System",
        defaults={
            'message': 'Touch and Solve Micro Finance Co-operative System is live and active.',
            'link': '/portal/admin/',
            'notification_type': 'SUCCESS',
            'is_read': False,
        }
    )

    print("  - Sample Members and Savings Accounts (0.00 balance) initialized without past money history.")
    print("\nDatabase Seeding Complete!")
    print("--------------------------------------------------")
    print("Login Credentials:")
    print("  * Admin (Owner):  username: admin    | password: admin123")
    print("  * Officer 1:      username: officer1 | password: 123456")
    print("  * Officer 2:      username: officer2 | password: 123456")
    print("  * Member 1:       username: rahim    | password: 123456")
    print("  * Member 2:       username: fatema   | password: 123456")
    print("  * Member 3:       username: kamal    | password: 123456")
    print("--------------------------------------------------")

if __name__ == '__main__':
    seed()
