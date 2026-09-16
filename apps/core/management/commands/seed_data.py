from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount
from apps.loans.models import LoanScheme
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Seeds initial demo and admin data for Touch & Solve Microfinance"

    def handle(self, *args, **options):
        self.stdout.write("[*] Seeding Touch and Solve Microfinance Database...")

        # 1. Admin
        admin_user, _ = CustomUser.objects.get_or_create(
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
        self.stdout.write("  - Admin User: admin (password: admin123)")

        # 2. Officers
        officers_data = [
            ('officer1', 'Tareq', 'Hasan', 'officer1@touchandsolve.com', '01811000001'),
            ('officer2', 'Salma', 'Khatun', 'officer2@touchandsolve.com', '01811000002'),
        ]
        officers = {}
        for uname, fname, lname, email, phone in officers_data:
            officer, _ = CustomUser.objects.get_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'first_name': fname,
                    'last_name': lname,
                    'role': 'OFFICER',
                    'phone': phone,
                    'is_staff': True,
                }
            )
            officer.set_password('123456')
            officer.save()
            officers[uname] = officer
        self.stdout.write("  - Officers: officer1, officer2 (password: 123456)")

        # 3. Loan Schemes
        schemes = [
            ("Micro Enterprise Loan", Decimal('10000.00'), Decimal('200000.00'), Decimal('10.00'), 12, 'MONTHLY',
             'Designed for small business development and retail store inventory.'),
            ("Weekly Small Trade Loan", Decimal('5000.00'), Decimal('50000.00'), Decimal('8.00'), 6, 'WEEKLY',
             'Weekly repayment loan for daily vegetable, grocery and trade vendors.'),
            ("Emergency Assistance Loan", Decimal('5000.00'), Decimal('30000.00'), Decimal('5.00'), 3, 'MONTHLY',
             'Low interest short-term emergency funds for members in need.'),
        ]
        for name, min_amt, max_amt, rate, duration, freq, desc in schemes:
            LoanScheme.objects.get_or_create(
                name=name,
                defaults={
                    'min_amount': min_amt,
                    'max_amount': max_amt,
                    'interest_rate_percent': rate,
                    'duration_months': duration,
                    'installment_frequency': freq,
                    'description': desc,
                    'is_active': True,
                }
            )
        self.stdout.write("  - Loan Schemes created (Micro Enterprise, Weekly Trade, Emergency)")

        # 4. Members
        members_data = [
            ('rahim', 'Rahim', 'Uddin', 'rahim@gmail.com', '01712345671', 'TNS-MEM-0001', '199026920110001', 'MALE',
             date(1990, 5, 12), 'Abdul Jabbar', 'Amena Begum', 'Grocery Shop Owner', 'House 12, Road 4, Mirpur-10, Dhaka',
             'Vill: Sonapur, Thana: Begumganj, Dist: Noakhali', 'Rashida Sultana', 'Wife', '01712345672', '199326920110002',
             officers['officer1'], 'SAV-0001'),
            ('fatema', 'Fatema', 'Begum', 'fatema@gmail.com', '01712345673', 'TNS-MEM-0002', '199226920110003', 'FEMALE',
             date(1992, 8, 20), 'Anwar Hossain', 'Sufia Khatun', 'Boutique Tailor', 'Sector 7, Uttara, Dhaka',
             'Vill: Rampur, Dist: Comilla', 'Anwar Hossain', 'Husband', '01712345674', 'SAV-0002',
             officers['officer2'], 'SAV-0002'),
            ('kamal', 'Kamal', 'Hossain', 'kamal@gmail.com', '01712345675', 'TNS-MEM-0003', '199526920110005', 'MALE',
             date(1995, 3, 15), 'Mofizur Rahman', 'Khaleda Begum', 'Poultry Farmer', 'Savar, Dhaka',
             'Savar, Dhaka', 'Shirin Akter', 'Sister', '01712345676', 'SAV-0003',
             officers['officer1'], 'SAV-0003'),
        ]

        for m in members_data:
            uname, fn, ln, email, phone, mem_id, nid, gender, dob, father, mother, occ, pres_addr, perm_addr, nom_name, nom_rel, nom_phone, nom_nid, officer, acc_num = m
            u, _ = CustomUser.objects.get_or_create(
                username=uname,
                defaults={'first_name': fn, 'last_name': ln, 'email': email, 'phone': phone, 'role': 'MEMBER'}
            )
            u.set_password('123456')
            u.save()

            profile, _ = MemberProfile.objects.get_or_create(
                user=u,
                defaults={
                    'member_id': mem_id,
                    'nid_number': nid,
                    'gender': gender,
                    'date_of_birth': dob,
                    'father_or_husband_name': father,
                    'mother_name': mother,
                    'occupation': occ,
                    'present_address': pres_addr,
                    'permanent_address': perm_addr,
                    'nominee_name': nom_name,
                    'nominee_relation': nom_rel,
                    'nominee_phone': nom_phone,
                    'nominee_nid': nom_nid,
                    'assigned_officer': officer,
                    'status': 'ACTIVE',
                }
            )

            sav, _ = SavingsAccount.objects.get_or_create(
                member=profile,
                defaults={'account_number': acc_num, 'balance': Decimal('0.00')}
            )
            sav.balance = Decimal('0.00')
            sav.save()

        Notification.objects.get_or_create(
            user=admin_user,
            title="Welcome to Touch & Solve System",
            defaults={
                'message': 'Touch and Solve Microfinance Co-operative System is live and active.',
                'link': '/portal/admin/',
                'notification_type': 'SUCCESS',
                'is_read': False,
            }
        )

        self.stdout.write(self.style.SUCCESS("Database Seeding Complete!"))
