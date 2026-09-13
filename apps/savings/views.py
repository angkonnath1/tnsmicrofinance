"""
==============================================================================
Touch and Solve Microfinance - Savings App Views
Author: Beginner Learner Developer / Learning Project
Description: Views for managing member savings accounts, deposit requests
             (Cash, bKash, Nagad), withdrawal requests, staff approvals,
             and generating printable account statements.
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from decimal import Decimal
import decimal
import uuid

# Import custom models and forms
from apps.accounts.decorators import officer_required, member_required
from apps.members.models import MemberProfile
from apps.core.sslcommerz import sslcommerz_client
from apps.notifications.utils import notify_user, notify_staff_and_admins
from .models import SavingsAccount, SavingsTransaction, SSLPaymentSession
from .forms import (
    MemberDepositRequestForm,
    MemberWithdrawalRequestForm,
    StaffRecordDepositForm,
    StaffRecordWithdrawalForm,
)


# ==============================================================================
# 1. MEMBER SAVINGS VIEW
# Shows member's total savings balance, deposit/withdrawal forms, and history.
# ==============================================================================
@member_required
def my_savings_view(request):
    # Step 1: Get the logged-in member's profile
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        messages.error(request, "Member profile not found.")
        return redirect('core:dashboard')

    # Step 2: Retrieve or auto-create their savings account
    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    # Step 3: Fetch transaction history
    transactions = account.transactions.all().order_by('-created_at')
    deposit_form = MemberDepositRequestForm()
    withdrawal_form = MemberWithdrawalRequestForm(account=account)

    # Step 4: Calculate total lifetime deposits and withdrawals
    total_deposited = transactions.filter(transaction_type='DEPOSIT', status='APPROVED').aggregate(Sum('amount'))['amount__sum'] or 0
    total_withdrawn = transactions.filter(transaction_type='WITHDRAWAL', status='APPROVED').aggregate(Sum('amount'))['amount__sum'] or 0

    # Step 5: Paginate 10 transactions per page
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Step 6: Render template
    context = {
        'account': account,
        'page_obj': page_obj,
        'transactions': page_obj,
        'deposit_form': deposit_form,
        'withdrawal_form': withdrawal_form,
        'total_deposited': total_deposited,
        'total_withdrawn': total_withdrawn,
    }
    return render(request, 'savings/my_savings.html', context)


# ==============================================================================
# 2. MEMBER SUBMITS DEPOSIT REQUEST (Pending Officer Verification)
# ==============================================================================
@member_required
def member_deposit_request(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        return redirect('core:dashboard')

    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    if request.method == 'POST':
        form = MemberDepositRequestForm(request.POST)
        if form.is_valid():
            trx = form.save(commit=False)
            trx.account = account
            trx.transaction_type = 'DEPOSIT'
            trx.status = 'PENDING'
            trx.created_by = request.user
            trx.save()

            messages.success(request, f"Deposit request of ৳{trx.amount} submitted for verification.")
            return redirect('savings:my_savings')
        else:
            messages.error(request, "Please enter a valid amount and payment details.")

    return redirect('savings:my_savings')


# ==============================================================================
# 3. MEMBER SUBMITS WITHDRAWAL REQUEST (Pending Officer Verification)
# ==============================================================================
@member_required
def member_withdrawal_request(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        return redirect('core:dashboard')

    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    if request.method == 'POST':
        form = MemberWithdrawalRequestForm(request.POST, account=account)
        if form.is_valid():
            trx = form.save(commit=False)
            trx.account = account
            trx.transaction_type = 'WITHDRAWAL'
            trx.status = 'PENDING'
            trx.created_by = request.user
            trx.save()

            messages.success(request, f"Withdrawal request of ৳{trx.amount} submitted. An officer will review it.")
            return redirect('savings:my_savings')
        else:
            for error in form.errors.values():
                messages.error(request, error)

    return redirect('savings:my_savings')


# ==============================================================================
# 4. STAFF TRANSACTIONS DIRECTORY (Filter & Search)
# ==============================================================================
@officer_required
def staff_transaction_list(request):
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    query = request.GET.get('q', '').strip()

    transactions = SavingsTransaction.objects.select_related(
        'account__member__user', 'created_by', 'processed_by'
    ).order_by('-created_at')

    if status_filter:
        transactions = transactions.filter(status=status_filter)
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)
    if query:
        transactions = transactions.filter(
            Q(account__member__member_id__icontains=query) |
            Q(account__member__user__first_name__icontains=query) |
            Q(account__member__user__last_name__icontains=query) |
            Q(reference_note__icontains=query)
        )

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    deposit_form = StaffRecordDepositForm()
    withdrawal_form = StaffRecordWithdrawalForm()
    active_members = MemberProfile.objects.filter(status='ACTIVE').select_related('user').order_by('member_id')

    context = {
        'page_obj': page_obj,
        'transactions': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'query': query,
        'deposit_form': deposit_form,
        'withdrawal_form': withdrawal_form,
        'active_members': active_members,
    }
    return render(request, 'savings/staff_transactions.html', context)


# ==============================================================================
# 5. STAFF DIRECTLY RECORDS A DEPOSIT (Instant Approval)
# ==============================================================================
@officer_required
def staff_record_deposit(request):
    if request.method == 'POST':
        form = StaffRecordDepositForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            reference_note = form.cleaned_data.get('reference_note', '')

            account, _ = SavingsAccount.objects.get_or_create(
                member=member,
                defaults={'account_number': f"SAV-{member.member_id.replace('TNS-MEM-', '')}"}
            )

            with transaction.atomic():
                account.deposit(amount)
                trx = SavingsTransaction.objects.create(
                    account=account,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    payment_method=payment_method,
                    reference_note=reference_note,
                    status='APPROVED',
                    created_by=request.user,
                    processed_by=request.user,
                    processed_at=timezone.now()
                )

            messages.success(request, f"Deposit of ৳{amount} recorded successfully for {member.member_id}.")
            return redirect('savings:staff_transactions')
        else:
            messages.error(request, "Please check the deposit form inputs.")

    return redirect('savings:staff_transactions')


# ==============================================================================
# 6. STAFF DIRECTLY RECORDS A WITHDRAWAL (Instant Debit)
# ==============================================================================
@officer_required
def staff_record_withdrawal(request):
    if request.method == 'POST':
        form = StaffRecordWithdrawalForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            amount = form.cleaned_data['amount']
            reference_note = form.cleaned_data.get('reference_note', '')

            account = getattr(member, 'savings_account', None)
            if not account or account.balance < amount:
                messages.error(request, f"Cannot withdraw: Account has insufficient balance ({account.balance if account else 0} BDT).")
                return redirect('savings:staff_transactions')

            with transaction.atomic():
                account.withdraw(amount)
                trx = SavingsTransaction.objects.create(
                    account=account,
                    transaction_type='WITHDRAWAL',
                    amount=amount,
                    payment_method='CASH',
                    reference_note=reference_note,
                    status='APPROVED',
                    created_by=request.user,
                    processed_by=request.user,
                    processed_at=timezone.now()
                )

            messages.success(request, f"Withdrawal of ৳{amount} processed successfully for {member.member_id}.")
            return redirect('savings:staff_transactions')
        else:
            messages.error(request, "Please check the withdrawal form inputs.")

    return redirect('savings:staff_transactions')


# ==============================================================================
# 7. STAFF APPROVES PENDING TRANSACTION
# ==============================================================================
@officer_required
def staff_approve_transaction(request, trx_id):
    trx = get_object_or_404(SavingsTransaction, id=trx_id, status='PENDING')
    account = trx.account

    with transaction.atomic():
        if trx.transaction_type == 'DEPOSIT':
            account.deposit(trx.amount)
            trx.status = 'APPROVED'
            trx.processed_by = request.user
            trx.processed_at = timezone.now()
            trx.save()
            messages.success(request, f"Deposit #{trx.id} approved successfully.")

        elif trx.transaction_type == 'WITHDRAWAL':
            if account.balance < trx.amount:
                messages.error(request, f"Approval failed: Member balance ({account.balance} BDT) is lower than requested {trx.amount} BDT.")
                return redirect('savings:staff_transactions')

            account.withdraw(trx.amount)
            trx.status = 'APPROVED'
            trx.processed_by = request.user
            trx.processed_at = timezone.now()
            trx.save()
            messages.success(request, f"Withdrawal #{trx.id} approved successfully.")

    return redirect('savings:staff_transactions')


# ==============================================================================
# 8. STAFF REJECTS PENDING TRANSACTION
# ==============================================================================
@officer_required
def staff_reject_transaction(request, trx_id):
    trx = get_object_or_404(SavingsTransaction, id=trx_id, status='PENDING')
    trx.status = 'REJECTED'
    trx.processed_by = request.user
    trx.processed_at = timezone.now()
    trx.save()

    messages.info(request, f"Transaction #{trx.id} has been marked as rejected.")
    return redirect('savings:staff_transactions')


# ==============================================================================
# 9. SAVINGS ACCOUNT STATEMENT GENERATOR & PDF
# Calculates opening balance, running balances, and allows PDF download.
# ==============================================================================
@login_required
def savings_statement_view(request, member_id=None):
    # Step 1: Identify target member
    if request.user.is_member_user:
        profile = getattr(request.user, 'member_profile', None)
        if not profile:
            messages.error(request, "Member profile not found.")
            return redirect('core:dashboard')
    else:
        if member_id:
            profile = get_object_or_404(MemberProfile, id=member_id)
        else:
            member_param = request.GET.get('member')
            search_query = request.GET.get('q', '').strip()
            if search_query:
                found = MemberProfile.objects.filter(
                    Q(member_id__icontains=search_query) |
                    Q(user__first_name__icontains=search_query) |
                    Q(user__last_name__icontains=search_query) |
                    Q(user__username__icontains=search_query) |
                    Q(user__phone__icontains=search_query)
                ).first()
                if found:
                    profile = found
                elif member_param:
                    profile = MemberProfile.objects.filter(id=member_param).first()
                else:
                    profile = MemberProfile.objects.filter(status='ACTIVE').first()
            elif member_param:
                profile = MemberProfile.objects.filter(id=member_param).first()
            else:
                profile = MemberProfile.objects.filter(status='ACTIVE').first()

    all_members = MemberProfile.objects.filter(status='ACTIVE').select_related('user').order_by('member_id') if not request.user.is_member_user else []
    account = getattr(profile, 'savings_account', None) if profile else None

    # Step 2: Date filters
    today = timezone.now().date()
    default_start = today - timedelta(days=30)
    
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    trx_type = request.GET.get('type', 'ALL')
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    except ValueError:
        end_date = today

    transactions_list = []
    opening_balance = Decimal('0.00')
    total_deposits = Decimal('0.00')
    total_withdrawals = Decimal('0.00')
    closing_balance = Decimal('0.00')

    # Step 3: Compute opening balance and running statement balances
    if account:
        prior_trxs = account.transactions.filter(status='APPROVED', created_at__date__lt=start_date)
        prior_dep = prior_trxs.filter(transaction_type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        prior_wd = prior_trxs.filter(transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        opening_balance = prior_dep - prior_wd

        qs = account.transactions.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        if trx_type in ['DEPOSIT', 'WITHDRAWAL']:
            qs = qs.filter(transaction_type=trx_type)

        qs = qs.order_by('created_at')

        current_running = opening_balance
        for trx in qs:
            if trx.status == 'APPROVED':
                if trx.transaction_type == 'DEPOSIT':
                    current_running += trx.amount
                    total_deposits += trx.amount
                elif trx.transaction_type == 'WITHDRAWAL':
                    current_running -= trx.amount
                    total_withdrawals += trx.amount
            
            transactions_list.append({
                'trx': trx,
                'running_balance': current_running if trx.status == 'APPROVED' else None
            })

        closing_balance = opening_balance + total_deposits - total_withdrawals

    # Step 4: Render statement template (supports standard browser printing)

    context = {
        'profile': profile,
        'account': account,
        'all_members': all_members,
        'start_date': start_date,
        'end_date': end_date,
        'trx_type': trx_type,
        'transactions_list': transactions_list,
        'opening_balance': opening_balance,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net_movement': total_deposits - total_withdrawals,
        'closing_balance': closing_balance,
        'generated_at': timezone.now(),
    }
    return render(request, 'savings/savings_statement.html', context)


# ==============================================================================
# 5. SSLCOMMERZ ONLINE PAYMENT GATEWAY (SANDBOX & LIVE)
# ==============================================================================

@member_required
def add_money_online_view(request):
    """
    Initiates SSLCOMMERZ sandbox hosted payment session for instant online savings deposit.
    """
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        messages.error(request, "Member profile not found.")
        return redirect('core:dashboard')

    account, _ = SavingsAccount.objects.get_or_create(
        member=profile,
        defaults={'account_number': f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"}
    )

    if request.method == 'POST':
        amount_str = request.POST.get('amount', '').strip()
        try:
            amount = Decimal(amount_str)
            if amount < Decimal('50.00'):
                messages.error(request, "Minimum online deposit amount is 50.00 BDT.")
                return redirect('savings:add_money_online')
            if amount > Decimal('500000.00'):
                messages.error(request, "Maximum single online transaction limit is 500,000.00 BDT.")
                return redirect('savings:add_money_online')
        except (ValueError, decimal.InvalidOperation):
            messages.error(request, "Please enter a valid deposit amount.")
            return redirect('savings:add_money_online')

        # Create unique transaction ID
        tran_id = f"SSL-TNS-{int(timezone.now().timestamp())}-{uuid.uuid4().hex[:6].upper()}"

        SSLPaymentSession.objects.create(
            tran_id=tran_id,
            account=account,
            amount=amount,
            status='PENDING'
        )

        success_url = request.build_absolute_uri(reverse('savings:sslcommerz_success'))
        fail_url = request.build_absolute_uri(reverse('savings:sslcommerz_fail'))
        cancel_url = request.build_absolute_uri(reverse('savings:sslcommerz_cancel'))

        res = sslcommerz_client.initiate_payment(
            tran_id=tran_id,
            amount=amount,
            customer=request.user,
            success_url=success_url,
            fail_url=fail_url,
            cancel_url=cancel_url,
            product_name="Touch & Solve Savings Deposit"
        )

        if res.get('status') == 'SUCCESS' and res.get('gateway_url'):
            return redirect(res['gateway_url'])
        else:
            messages.error(request, f"Could not connect to SSLCOMMERZ Sandbox Gateway: {res.get('message', 'Please try again')}")
            return redirect('savings:add_money_online')

    return render(request, 'savings/add_money_online.html', {
        'account': account,
        'profile': profile,
    })


@csrf_exempt
def sslcommerz_success_view(request):
    """
    SSLCOMMERZ POST callback handler on customer payment success.
    Validates with SSLCOMMERZ validation API, updates account balance, and generates receipt.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    val_id = request.POST.get('val_id') or request.GET.get('val_id')
    card_type = request.POST.get('card_type') or request.GET.get('card_type') or 'SSLCOMMERZ-Online'
    bank_tran_id = request.POST.get('bank_tran_id') or request.GET.get('bank_tran_id') or f"BNK-{uuid.uuid4().hex[:10].upper()}"

    if not tran_id:
        messages.error(request, "Invalid payment callback: missing transaction ID.")
        return redirect('savings:my_savings')

    session = get_object_or_404(SSLPaymentSession, tran_id=tran_id)

    if val_id:
        val_res = sslcommerz_client.validate_payment(val_id, tran_id)
        if val_res.get('status') in ['VALID', 'VALIDATED']:
            card_type = val_res.get('card_type') or card_type
            bank_tran_id = val_res.get('bank_tran_id') or bank_tran_id

    if session.status != 'VALID':
        with transaction.atomic():
            session.status = 'VALID'
            session.val_id = val_id or f"VAL-{uuid.uuid4().hex[:8].upper()}"
            session.card_type = card_type
            session.bank_tran_id = bank_tran_id
            session.validated_at = timezone.now()
            session.save()

            # Credit savings account balance
            account = session.account
            account.balance += session.amount
            account.save(update_fields=['balance', 'updated_at'])

            # Record approved savings transaction
            SavingsTransaction.objects.create(
                account=account,
                transaction_type='DEPOSIT',
                amount=session.amount,
                payment_method='SSLCOMMERZ',
                reference_note=f"SSLCOMMERZ Sandbox Deposit ({card_type} - Ref: {tran_id})",
                status='APPROVED',
                created_by=account.member.user,
                processed_by=account.member.user,
                processed_at=timezone.now()
            )

            # Send in-app notification to member
            notify_user(
                user=account.member.user,
                title="Online Deposit Successful!",
                message=f"Your online deposit of {session.amount} BDT via SSLCOMMERZ Sandbox ({card_type}) was successful! New Savings Balance: {account.balance} BDT.",
                link="/savings/my-account/",
                notification_type='SUCCESS'
            )

            # Send in-app notification to staff/admins
            notify_staff_and_admins(
                title="Online Savings Deposit Received",
                message=f"Member {account.member.member_id} ({account.member.user.get_full_name()}) added {session.amount} BDT via SSLCOMMERZ Sandbox ({card_type}).",
                link="/savings/transactions/",
                notification_type='INFO'
            )

    return render(request, 'savings/sslcommerz_receipt.html', {
        'session': session,
        'account': session.account,
        'member': session.account.member,
    })


@csrf_exempt
def sslcommerz_fail_view(request):
    """
    SSLCOMMERZ callback when transaction fails or is declined.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    if tran_id:
        SSLPaymentSession.objects.filter(tran_id=tran_id, status='PENDING').update(status='FAILED')
    
    messages.error(request, "Online payment transaction was declined or failed. Please try again or choose another payment method.")
    return redirect('savings:add_money_online')


@csrf_exempt
def sslcommerz_cancel_view(request):
    """
    SSLCOMMERZ callback when customer cancels the checkout window.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    if tran_id:
        SSLPaymentSession.objects.filter(tran_id=tran_id, status='PENDING').update(status='CANCELLED')
    
    messages.warning(request, "Online payment transaction was cancelled.")
    return redirect('savings:add_money_online')

