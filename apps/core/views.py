from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.decorators import admin_required, officer_required, member_required
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.loans.models import LoanApplication, LoanInstallment


def dashboard_dispatcher(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.user.is_admin_user or request.user.is_superuser:
        return redirect('core:admin_dashboard')
    elif request.user.is_officer_user:
        return redirect('core:officer_dashboard')
    return redirect('core:member_dashboard')


@member_required
def member_dashboard(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        profile, _ = MemberProfile.objects.get_or_create(user=request.user)

    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    active_loans = profile.loans.filter(status='DISBURSED')
    total_loan_outstanding = sum(loan.remaining_balance for loan in active_loans)

    next_installment = LoanInstallment.objects.filter(
        loan__member=profile,
        status='PENDING'
    ).order_by('due_date').first()

    return render(request, 'dashboard/member_dashboard.html', {
        'profile': profile,
        'account': account,
        'active_loans': active_loans,
        'total_loan_outstanding': total_loan_outstanding,
        'next_installment': next_installment,
        'recent_transactions': account.transactions.all().order_by('-created_at')[:5],
        'recent_loans': profile.loans.all().order_by('-applied_at')[:5],
    })


@officer_required
def officer_dashboard(request):
    today = timezone.now().date()

    mem_stats = MemberProfile.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='ACTIVE')),
        pending=Count('id', filter=Q(status='PENDING')),
    )

    sav_stats = SavingsTransaction.objects.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        today_deposit=Sum('amount', filter=Q(transaction_type='DEPOSIT', status='APPROVED', created_at__date=today)),
    )

    loan_stats = LoanApplication.objects.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        active=Count('id', filter=Q(status='DISBURSED')),
    )

    today_deposit_collected = sav_stats['today_deposit'] or Decimal('0.00')
    today_installment_collected = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=today
    ).aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

    return render(request, 'dashboard/officer_dashboard.html', {
        'total_members': mem_stats['total'],
        'active_members': mem_stats['active'],
        'pending_members_count': mem_stats['pending'],
        'pending_members': MemberProfile.objects.filter(status='PENDING').select_related('user').order_by('-created_at')[:5],
        'pending_savings_count': sav_stats['pending'],
        'pending_loans_count': loan_stats['pending'],
        'active_loans_count': loan_stats['active'],
        'today_deposit_collected': today_deposit_collected,
        'today_installment_collected': today_installment_collected,
        'today_total_collection': today_deposit_collected + today_installment_collected,
        'today_due_installments': LoanInstallment.objects.filter(
            due_date=today, status='PENDING'
        ).select_related('loan__member__user')[:10],
        'overdue_installments': LoanInstallment.objects.filter(
            due_date__lt=today, status='PENDING'
        ).select_related('loan__member__user').order_by('due_date')[:10],
        'pending_deposits': SavingsTransaction.objects.filter(
            status='PENDING'
        ).select_related('account__member__user')[:5],
        'pending_loans': LoanApplication.objects.filter(
            status='PENDING'
        ).select_related('member__user')[:5],
    })


@admin_required
def admin_dashboard(request):
    total_officers = CustomUser.objects.filter(role='OFFICER').count()

    mem_stats = MemberProfile.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
    )

    total_savings_balance = SavingsAccount.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

    sav_stats = SavingsTransaction.objects.aggregate(
        deposits=Sum('amount', filter=Q(transaction_type='DEPOSIT', status='APPROVED')),
        withdrawals=Sum('amount', filter=Q(transaction_type='WITHDRAWAL', status='APPROVED')),
        pending=Count('id', filter=Q(status='PENDING')),
    )

    loan_stats = LoanApplication.objects.aggregate(
        disbursed_count=Count('id', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        disbursed_amount=Sum('principal_amount', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        expected_payable=Sum('total_payable', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        loan_repaid=Sum('total_paid', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        profit_interest=Sum('total_interest', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        pending=Count('id', filter=Q(status='PENDING')),
    )

    total_expected_payable = loan_stats['expected_payable'] or Decimal('0.00')
    total_loan_repaid = loan_stats['loan_repaid'] or Decimal('0.00')
    total_loan_outstanding = max(Decimal('0.00'), total_expected_payable - total_loan_repaid)

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_officers': total_officers,
        'total_members': mem_stats['total'],
        'total_savings_balance': total_savings_balance,
        'total_deposit_sum': sav_stats['deposits'] or Decimal('0.00'),
        'total_withdrawal_sum': sav_stats['withdrawals'] or Decimal('0.00'),
        'total_loans_disbursed_count': loan_stats['disbursed_count'],
        'total_disbursed_amount': loan_stats['disbursed_amount'] or Decimal('0.00'),
        'total_loan_repaid': total_loan_repaid,
        'total_loan_outstanding': total_loan_outstanding,
        'total_profit_interest_earned': loan_stats['profit_interest'] or Decimal('0.00'),
        'pending_loans_count': loan_stats['pending'],
        'pending_savings_count': sav_stats['pending'],
        'pending_members_count': mem_stats['pending'],
        'recent_transactions': SavingsTransaction.objects.select_related(
            'account__member__user', 'created_by'
        ).order_by('-created_at')[:8],
        'recent_loans': LoanApplication.objects.select_related('member__user').order_by('-applied_at')[:8],
    })


@officer_required
def collection_sheet_view(request):
    today = timezone.now().date()
    date_str = request.GET.get('date', '').strip()
    officer_id = request.GET.get('officer', '').strip()

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
    except ValueError:
        selected_date = today

    all_officers = CustomUser.objects.filter(role='OFFICER').order_by('first_name')

    members_qs = MemberProfile.objects.filter(status='ACTIVE').select_related(
        'user', 'savings_account', 'assigned_officer'
    ).prefetch_related('loans__installments').order_by('member_id')

    if officer_id:
        members_qs = members_qs.filter(assigned_officer_id=officer_id)

    deposits_qs = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by')

    if officer_id:
        deposits_qs = deposits_qs.filter(account__member__assigned_officer_id=officer_id)

    dep_agg = deposits_qs.aggregate(
        total=Sum('amount'),
        cash=Sum('amount', filter=Q(payment_method='CASH')),
        digital=Sum('amount', filter=Q(payment_method__in=['BKASH', 'NAGAD', 'BANK']))
    )
    total_deposit_collection = dep_agg['total'] or Decimal('0.00')
    cash_deposits = dep_agg['cash'] or Decimal('0.00')
    digital_deposits = dep_agg['digital'] or Decimal('0.00')

    installments_paid_qs = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=selected_date
    ).select_related('loan__member__user', 'collected_by')

    if officer_id:
        installments_paid_qs = installments_paid_qs.filter(loan__member__assigned_officer_id=officer_id)

    total_installment_collection = installments_paid_qs.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

    due_installments_qs = LoanInstallment.objects.filter(
        due_date=selected_date,
        status__in=['PENDING', 'OVERDUE']
    ).select_related('loan__member__user')

    if officer_id:
        due_installments_qs = due_installments_qs.filter(loan__member__assigned_officer_id=officer_id)

    expected_installment_amount = due_installments_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    grand_total_collected = total_deposit_collection + total_installment_collection

    return render(request, 'dashboard/collection_sheet.html', {
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
    })


@admin_required
def financial_reports_view(request):
    sav_agg = SavingsTransaction.objects.filter(status='APPROVED').aggregate(
        deposits=Sum('amount', filter=Q(transaction_type='DEPOSIT')),
        withdrawals=Sum('amount', filter=Q(transaction_type='WITHDRAWAL')),
    )
    total_deposits = sav_agg['deposits'] or Decimal('0.00')
    total_withdrawals = sav_agg['withdrawals'] or Decimal('0.00')

    total_loans_given = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED']
    ).aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')
    total_repayments_collected = LoanApplication.objects.aggregate(Sum('total_paid'))['total_paid__sum'] or Decimal('0.00')

    net_cash_inflow = (total_deposits + total_repayments_collected) - (total_withdrawals + total_loans_given)

    return render(request, 'dashboard/financial_reports.html', {
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_loans_given': total_loans_given,
        'total_repayments_collected': total_repayments_collected,
        'net_cash_inflow': net_cash_inflow,
        'recent_transactions': SavingsTransaction.objects.filter(status='APPROVED').select_related('account__member__user').order_by('-processed_at')[:25],
        'all_loans': LoanApplication.objects.filter(status__in=['DISBURSED', 'COMPLETED']).select_related('member__user').order_by('-disbursed_at')[:25],
    })


@admin_required
def daily_master_transactions_view(request):
    today = timezone.now().date()
    date_str = request.GET.get('date', '').strip()

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
    except ValueError:
        selected_date = today

    deposits = SavingsTransaction.objects.filter(
        transaction_type='DEPOSIT',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by').order_by('created_at')

    withdrawals = SavingsTransaction.objects.filter(
        transaction_type='WITHDRAWAL',
        status='APPROVED',
        created_at__date=selected_date
    ).select_related('account__member__user', 'created_by', 'processed_by').order_by('created_at')

    disbursements = LoanApplication.objects.filter(
        status__in=['DISBURSED', 'COMPLETED'],
        disbursed_at__date=selected_date
    ).select_related('member__user', 'loan_product', 'approved_by').order_by('disbursed_at')

    installments_paid = LoanInstallment.objects.filter(
        status='PAID',
        paid_date=selected_date
    ).select_related('loan__member__user', 'collected_by').order_by('id')

    dep_agg = deposits.aggregate(
        total=Sum('amount'),
        cash=Sum('amount', filter=Q(payment_method='CASH'))
    )
    total_deposits = dep_agg['total'] or Decimal('0.00')
    cash_deposits = dep_agg['cash'] or Decimal('0.00')

    total_withdrawals = withdrawals.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_disbursed = disbursements.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal('0.00')

    inst_agg = installments_paid.aggregate(
        total=Sum('paid_amount'),
        principal=Sum('principal_amount'),
        interest=Sum('interest_amount'),
        cash=Sum('paid_amount', filter=Q(payment_method='CASH')),
    )
    total_repayments = inst_agg['total'] or Decimal('0.00')
    total_principal_repaid = inst_agg['principal'] or Decimal('0.00')
    total_interest_repaid = inst_agg['interest'] or Decimal('0.00')
    cash_installments = inst_agg['cash'] or Decimal('0.00')

    gross_inflow = total_deposits + total_repayments
    gross_outflow = total_withdrawals + total_disbursed
    net_cashflow = gross_inflow - gross_outflow
    cash_inflow = cash_deposits + cash_installments
    digital_inflow = gross_inflow - cash_inflow

    active_member_ids = (
        set(deposits.values_list('account__member_id', flat=True))
        | set(withdrawals.values_list('account__member_id', flat=True))
        | set(disbursements.values_list('member_id', flat=True))
        | set(installments_paid.values_list('loan__member_id', flat=True))
    )

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
        'total_trx_count': deposits.count() + withdrawals.count() + disbursements.count() + installments_paid.count(),
        'unique_members_count': len(active_member_ids),
    }

    return render(request, 'dashboard/daily_master_report.html', {
        'selected_date': selected_date,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'disbursements': disbursements,
        'installments_paid': installments_paid,
        'summary': summary_stats,
        'generated_at': timezone.now(),
    })
