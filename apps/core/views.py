"""
==============================================================================
Touch and Solve Microfinance - Core App Views
Author: Beginner Learner Developer / Learning Project
Description: Views for dispatching user dashboards (Admin, Officer, Member),
             generating daily collection sheets, and rendering financial reports.
==============================================================================
"""

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

# Import models and decorators
from apps.accounts.models import CustomUser
from apps.accounts.decorators import admin_required, officer_required, member_required
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.loans.models import LoanApplication, LoanInstallment


# ==============================================================================
# 1. DASHBOARD DISPATCHER
# Routes logged-in users to their respective dashboard based on their user role.
# ==============================================================================
def dashboard_dispatcher(request):
    # Step 1: If user is not logged in, redirect them to the login page
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    # Step 2: Check the user's role and redirect to the right dashboard
    if request.user.is_admin_user or request.user.is_superuser:
        return redirect('core:admin_dashboard')
    elif request.user.is_officer_user:
        return redirect('core:officer_dashboard')
    else:
        return redirect('core:member_dashboard')


# ==============================================================================
# 2. MEMBER DASHBOARD VIEW
# Shows member profile, savings balance, active loans, and recent transactions.
# ==============================================================================
@member_required
def member_dashboard(request):
    # Step 1: Get or create the member's profile for the logged-in user
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        profile, _ = MemberProfile.objects.get_or_create(user=request.user)

    # Step 2: Get or create the savings account linked to this member
    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    # Step 3: Fetch active loans that have been disbursed
    active_loans = profile.loans.filter(status='DISBURSED')
    total_loan_outstanding = sum(loan.remaining_balance for loan in active_loans)

    # Step 4: Find the next upcoming pending loan installment
    next_installment = LoanInstallment.objects.filter(
        loan__member=profile,
        status='PENDING'
    ).order_by('due_date').first()

    # Step 5: Get the 5 most recent savings transactions and loans
    recent_transactions = account.transactions.all().order_by('-created_at')[:5]
    recent_loans = profile.loans.all().order_by('-applied_at')[:5]

    # Step 6: Render the HTML template and pass all the data in the context dictionary
    context = {
        'profile': profile,
        'account': account,
        'active_loans': active_loans,
        'total_loan_outstanding': total_loan_outstanding,
        'next_installment': next_installment,
        'recent_transactions': recent_transactions,
        'recent_loans': recent_loans,
    }
    return render(request, 'dashboard/member_dashboard.html', context)


# ==============================================================================
# 3. OFFICER DASHBOARD VIEW
# Shows field metrics, daily collection summaries, and pending approval tasks.
# ==============================================================================
@officer_required
def officer_dashboard(request):
    today = timezone.now().date()

    # Step 1: Count total, active, and pending members
    total_members = MemberProfile.objects.count()
    active_members = MemberProfile.objects.filter(status='ACTIVE').count()
    pending_members_count = MemberProfile.objects.filter(status='PENDING').count()
    pending_members = MemberProfile.objects.filter(status='PENDING').select_related('user').order_by('-created_at')[:5]

    # Step 2: Calculate savings deposits collected today
    pending_savings_count = SavingsTransaction.objects.filter(status='PENDING').count()
    today_deposit_collected = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT',
        status='APPROVED',
        created_at__date=today
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Step 3: Calculate loan installments collected today
    pending_loans_count = LoanApplication.objects.filter(status='PENDING').count()
    active_loans_count = LoanApplication.objects.filter(status='DISBURSED').count()
    
    today_installment_collected = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=today
    ).aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

    # Step 4: Find due installments for today and overdue installments
    today_due_installments = LoanInstallment.objects.filter(
        due_date=today,
        status='PENDING'
    ).select_related('loan__member__user')[:10]

    overdue_installments = LoanInstallment.objects.filter(
        due_date__lt=today,
        status='PENDING'
    ).select_related('loan__member__user').order_by('due_date')[:10]

    # Step 5: Fetch pending action items requiring officer review
    pending_deposits = SavingsTransaction.objects.filter(
        status='PENDING'
    ).select_related('account__member__user')[:5]

    pending_loans = LoanApplication.objects.filter(
        status='PENDING'
    ).select_related('member__user')[:5]

    # Step 6: Package all variables into context and render template
    context = {
        'total_members': total_members,
        'active_members': active_members,
        'pending_members_count': pending_members_count,
        'pending_members': pending_members,
        'pending_savings_count': pending_savings_count,
        'pending_loans_count': pending_loans_count,
        'active_loans_count': active_loans_count,
        'today_deposit_collected': today_deposit_collected,
        'today_installment_collected': today_installment_collected,
        'today_total_collection': today_deposit_collected + today_installment_collected,
        'today_due_installments': today_due_installments,
        'overdue_installments': overdue_installments,
        'pending_deposits': pending_deposits,
        'pending_loans': pending_loans,
    }
    return render(request, 'dashboard/officer_dashboard.html', context)


# ==============================================================================
# 4. ADMIN DASHBOARD VIEW
# Executive financial overview, portfolio totals, profit, and activity stream.
# ==============================================================================
@admin_required
def admin_dashboard(request):
    today = timezone.now().date()

    # Step 1: Count system users and registered members
    total_officers = CustomUser.objects.filter(role='OFFICER').count()
    total_members = MemberProfile.objects.count()

    # Step 2: Sum all savings balances and transaction volumes
    total_savings_balance = SavingsAccount.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
    total_deposit_sum = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT', status='APPROVED'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_withdrawal_sum = SavingsTransaction.objects.filter(
        transaction_type='WITHDRAWAL', status='APPROVED'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Step 3: Aggregate loan disbursement, repayments, and outstanding balances
    total_loans_disbursed_count = LoanApplication.objects.filter(status__in=['DISBURSED', 'COMPLETED']).count()
    total_disbursed_amount = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED']
    ).aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')

    total_expected_payable = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED']
    ).aggregate(Sum('total_payable'))['total_payable__sum'] or Decimal('0.00')

    total_loan_repaid = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED']
    ).aggregate(Sum('total_paid'))['total_paid__sum'] or Decimal('0.00')

    total_loan_outstanding = max(Decimal('0.00'), total_expected_payable - total_loan_repaid)
    total_profit_interest_earned = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED']
    ).aggregate(Sum('total_interest'))['total_interest__sum'] or Decimal('0.00')

    # Step 4: Count pending approvals
    pending_loans_count = LoanApplication.objects.filter(status='PENDING').count()
    pending_savings_count = SavingsTransaction.objects.filter(status='PENDING').count()
    pending_members_count = MemberProfile.objects.filter(status='PENDING').count()

    # Step 5: Recent system activities
    recent_transactions = SavingsTransaction.objects.select_related(
        'account__member__user', 'created_by'
    ).order_by('-created_at')[:8]

    recent_loans = LoanApplication.objects.select_related(
        'member__user'
    ).order_by('-applied_at')[:8]

    # Step 6: Render Admin dashboard
    context = {
        'total_officers': total_officers,
        'total_members': total_members,
        'total_savings_balance': total_savings_balance,
        'total_deposit_sum': total_deposit_sum,
        'total_withdrawal_sum': total_withdrawal_sum,
        'total_loans_disbursed_count': total_loans_disbursed_count,
        'total_disbursed_amount': total_disbursed_amount,
        'total_loan_repaid': total_loan_repaid,
        'total_loan_outstanding': total_loan_outstanding,
        'total_profit_interest_earned': total_profit_interest_earned,
        'pending_loans_count': pending_loans_count,
        'pending_savings_count': pending_savings_count,
        'pending_members_count': pending_members_count,
        'recent_transactions': recent_transactions,
        'recent_loans': recent_loans,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# ==============================================================================
# 5. DAILY COLLECTION SHEET VIEW & PDF EXPORT
# Generates daily field collection sheets and allows exporting as PDF report.
# ==============================================================================
@officer_required
def collection_sheet_view(request):
    today = timezone.now().date()
    date_str = request.GET.get('date', '')
    officer_id = request.GET.get('officer', '')

    # Step 1: Parse the date from URL query parameter or fallback to today
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
    except ValueError:
        selected_date = today

    all_officers = CustomUser.objects.filter(role='OFFICER').order_by('first_name')

    # Step 2: Query active members and filter by officer if selected
    members_qs = MemberProfile.objects.filter(status='ACTIVE').select_related(
        'user', 'savings_account', 'assigned_officer'
    ).prefetch_related('loans__installments').order_by('member_id')

    if officer_id:
        members_qs = members_qs.filter(assigned_officer_id=officer_id)

    # Step 3: Query deposits collected on the selected date
    deposits_qs = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by')

    if officer_id:
        deposits_qs = deposits_qs.filter(account__member__assigned_officer_id=officer_id)

    total_deposit_collection = deposits_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Step 4: Query loan installments paid on the selected date
    installments_paid_qs = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=selected_date
    ).select_related('loan__member__user', 'collected_by')

    if officer_id:
        installments_paid_qs = installments_paid_qs.filter(loan__member__assigned_officer_id=officer_id)

    total_installment_collection = installments_paid_qs.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

    # Step 5: Calculate payment methods breakdown (Cash vs Digital)
    cash_deposits = deposits_qs.filter(payment_method='CASH').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    digital_deposits = deposits_qs.filter(payment_method__in=['BKASH', 'NAGAD', 'BANK']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Step 6: Find all installments due on the selected date
    due_installments_qs = LoanInstallment.objects.filter(
        due_date=selected_date,
        status__in=['PENDING', 'OVERDUE']
    ).select_related('loan__member__user')

    if officer_id:
        due_installments_qs = due_installments_qs.filter(loan__member__assigned_officer_id=officer_id)

    expected_installment_amount = due_installments_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    grand_total_collected = total_deposit_collection + total_installment_collection

    # Step 7: Render the HTML collection sheet page (supports standard browser printing)

    context = {
        'members': members_qs,
        'selected_date': selected_date,
        'all_officers': all_officers,
        'selected_officer_id': officer_id,
        'deposits': deposits_qs,
        'installments_paid': installments_paid_qs,
        'due_installments': due_installments_qs,
        'total_deposit_collection': total_deposit_collection,
        'total_installment_collection': total_installment_collection,
        'grand_total_collected': grand_total_collected,
        'cash_deposits': cash_deposits,
        'digital_deposits': digital_deposits,
        'expected_installment_amount': expected_installment_amount,
        'generated_at': timezone.now(),
    }
    return render(request, 'dashboard/collection_sheet.html', context)


# ==============================================================================
# 6. FINANCIAL REPORTS VIEW
# Shows total cash inflow, outflow, and net balance for the co-operative.
# ==============================================================================
@admin_required
def financial_reports_view(request):
    # Step 1: Calculate total deposits and repayments (Inflow)
    total_deposits = SavingsTransaction.objects.filter(transaction_type='DEPOSIT', status='APPROVED').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_withdrawals = SavingsTransaction.objects.filter(transaction_type='WITHDRAWAL', status='APPROVED').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_loans_given = LoanApplication.objects.filter(status__in=['DISBURSED', 'COMPLETED']).aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')
    total_repayments_collected = LoanApplication.objects.aggregate(Sum('total_paid'))['total_paid__sum'] or Decimal('0.00')

    # Step 2: Compute net cash inflow
    net_cash_inflow = (total_deposits + total_repayments_collected) - (total_withdrawals + total_loans_given)

    # Step 3: Fetch latest completed transactions and loans
    recent_transactions = SavingsTransaction.objects.filter(status='APPROVED').select_related('account__member__user').order_by('-processed_at')[:25]
    all_loans = LoanApplication.objects.filter(status__in=['DISBURSED', 'COMPLETED']).select_related('member__user').order_by('-disbursed_at')[:25]

    # Step 4: Render financial reports page
    context = {
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_loans_given': total_loans_given,
        'total_repayments_collected': total_repayments_collected,
        'net_cash_inflow': net_cash_inflow,
        'recent_transactions': recent_transactions,
        'all_loans': all_loans,
    }
    return render(request, 'dashboard/financial_reports.html', context)


# ==============================================================================
# 7. DAILY MASTER TRANSACTIONS & ALL-ACTIVITY AUDIT REPORT & PDF
# Allows Admin & Management to view and download a comprehensive daily PDF
# covering all savings deposits, withdrawals, loan disbursements, and repayments.
# ==============================================================================
@admin_required
def daily_master_transactions_view(request):
    today = timezone.now().date()
    date_str = request.GET.get('date', '').strip()

    # Step 1: Parse selected date or fallback to today
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
    except ValueError:
        selected_date = today

    # Step 2: Fetch all savings deposits on this date
    deposits = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by').order_by('created_at')

    # Step 3: Fetch all savings withdrawals on this date
    withdrawals = SavingsTransaction.objects.filter(
        transaction_type='WITHDRAWAL',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by', 'processed_by').order_by('created_at')

    # Step 4: Fetch all loans disbursed on this date
    disbursements = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED'],
        disbursed_at__date=selected_date
    ).select_related('member__user', 'loan_product', 'approved_by').order_by('disbursed_at')

    # Step 5: Fetch all loan installments collected on this date
    installments_paid = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=selected_date
    ).select_related('loan__member__user', 'collected_by').order_by('id')

    # Step 6: Compute financial totals and summary metrics
    total_deposits = deposits.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_withdrawals = withdrawals.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_disbursed = disbursements.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')
    total_repayments = installments_paid.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

    total_principal_repaid = installments_paid.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')
    total_interest_repaid = installments_paid.aggregate(Sum('interest_amount'))['interest_amount__sum'] or Decimal('0.00')

    # Cash Inflow vs Outflow vs Net Position
    gross_inflow = total_deposits + total_repayments
    gross_outflow = total_withdrawals + total_disbursed
    net_cashflow = gross_inflow - gross_outflow

    # Channel metrics
    cash_deposits = deposits.filter(payment_method='CASH').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    cash_installments = installments_paid.filter(payment_method='CASH').aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
    cash_inflow = cash_deposits + cash_installments
    digital_inflow = gross_inflow - cash_inflow

    total_trx_count = deposits.count() + withdrawals.count() + disbursements.count() + installments_paid.count()

    # Collect unique active members on this day
    active_member_ids = set()
    for d in deposits:
        active_member_ids.add(d.account.member_id)
    for w in withdrawals:
        active_member_ids.add(w.account.member_id)
    for l in disbursements:
        active_member_ids.add(l.member_id)
    for i in installments_paid:
        active_member_ids.add(i.loan.member_id)

    summary_stats = {
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_disbursed': total_disbursed,
        'total_repayments': total_repayments,
        'total_principal_repaid': total_principal_repaid,
        'total_interest_repaid': total_interest_repaid,
        'gross_inflow': gross_inflow,
        'gross_outflow': gross_outflow,
        'net_cashflow': net_cashflow,
        'cash_inflow': cash_inflow,
        'digital_inflow': digital_inflow,
        'total_trx_count': total_trx_count,
        'unique_members_count': len(active_member_ids),
    }

    # Step 7: Render the HTML dashboard view (supports standard browser printing)

    context = {
        'selected_date': selected_date,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'disbursements': disbursements,
        'installments_paid': installments_paid,
        'summary': summary_stats,
        'generated_at': timezone.now(),
    }
    return render(request, 'dashboard/daily_master_report.html', context)

