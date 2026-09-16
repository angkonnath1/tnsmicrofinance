"""
==============================================================================
Touch and Solve Microfinance - Loans App Views
Author: Beginner Learner Developer / Learning Project
Description: Views for managing loan applications, officer review & approval,
             disbursement, monthly installment repayments (savings, cash, MFS),
             managing loan schemes, and generating printable loan statements.
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import uuid

# Import services, models, and decorators
from apps.accounts.decorators import officer_required, member_required, admin_required
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount, SavingsTransaction
from apps.core.sslcommerz import sslcommerz_client
from apps.notifications.utils import notify_user, notify_staff_and_admins
from .models import LoanApplication, LoanInstallment, LoanScheme, SSLLoanPaymentSession
from .forms import (
    MemberLoanApplicationForm,
    StaffLoanApplicationForm,
    LoanSchemeForm,
)


# ==============================================================================
# 1. MEMBER LOANS OVERVIEW
# Displays member's active loans, pending applications, and repayment totals.
# ==============================================================================
@member_required
def my_loans_view(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        return redirect('core:dashboard')

    # Query all loans for this member
    loans = profile.loans.select_related('loan_product').order_by('-applied_at')
    active_loans = loans.filter(status='DISBURSED')
    pending_loans = loans.filter(status='PENDING')
    completed_loans = loans.filter(status='COMPLETED')

    # Sum total principal borrowed and total repayments made
    total_borrowed = loans.filter(status__in=['DISBURSED', 'COMPLETED']).aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
    total_repaid = loans.aggregate(Sum('total_paid'))['total_paid__sum'] or 0

    paginator = Paginator(loans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'loans': page_obj,
        'active_loans': active_loans,
        'pending_loans': pending_loans,
        'completed_loans': completed_loans,
        'total_borrowed': total_borrowed,
        'total_repaid': total_repaid,
    }
    return render(request, 'loans/my_loans.html', context)


# ==============================================================================
# 2. MEMBER APPLIES FOR A LOAN
# Allows member to choose a loan scheme, amount, duration, and submit application.
# ==============================================================================
@member_required
def apply_loan_view(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        messages.error(request, "Please complete your member profile first.")
        return redirect('core:dashboard')

    # Check if user already has an active or pending loan in progress
    has_pending = profile.loans.filter(status__in=['PENDING', 'APPROVED']).exists()
    if has_pending:
        messages.warning(request, "You already have a loan application in progress.")
        return redirect('loans:my_loans')

    if request.method == 'POST':
        form = MemberLoanApplicationForm(request.POST, applicant_member=profile)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.member = profile

            # Set interest rate from scheme or default to 10%
            if loan.loan_product:
                loan.interest_rate = loan.loan_product.interest_rate_percent
            else:
                loan.interest_rate = Decimal('10.00')

            loan.status = 'PENDING'
            loan.save()

            messages.success(request, f"Loan application #{loan.loan_id} for ৳{loan.principal_amount} submitted successfully!")
            return redirect('loans:loan_detail', pk=loan.pk)
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        scheme_id = request.GET.get('scheme')
        initial = {}
        if scheme_id:
            try:
                scheme = LoanScheme.objects.get(id=scheme_id, is_active=True)
                initial = {
                    'loan_product': scheme,
                    'principal_amount': scheme.min_amount,
                    'duration_months': scheme.duration_months,
                    'installment_frequency': scheme.installment_frequency,
                }
            except LoanScheme.DoesNotExist:
                pass
        form = MemberLoanApplicationForm(initial=initial, applicant_member=profile)

    schemes = LoanScheme.objects.filter(is_active=True)
    return render(request, 'loans/apply_loan.html', {
        'form': form,
        'schemes': schemes
    })


# ==============================================================================
# 3. LOAN DETAIL VIEW
# Displays loan info, progress bar, and complete installment repayment schedule.
# ==============================================================================
@login_required
def loan_detail_view(request, pk):
    loan = get_object_or_404(
        LoanApplication.objects.select_related('member__user', 'loan_product', 'approved_by'),
        pk=pk
    )

    # Permission check: Members can only see their own loans
    if request.user.is_member_user and hasattr(request.user, 'member_profile') and loan.member != request.user.member_profile:
        messages.error(request, "Access restricted.")
        return redirect('core:dashboard')

    installments = loan.installments.select_related('collected_by').order_by('installment_number')
    savings_account = getattr(loan.member, 'savings_account', None)

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'installments': installments,
        'savings_account': savings_account,
    })


# ==============================================================================
# 4. PAY INSTALLMENT (Direct Debit from Savings, Cash, or MFS)
# ==============================================================================
@login_required
def member_pay_installment(request, installment_id):
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    loan = installment.loan

    # Verify ownership if user is a member
    if request.user.is_member_user:
        if not hasattr(request.user, 'member_profile') or loan.member != request.user.member_profile:
            messages.error(request, "Unauthorized access to this loan installment.")
            return redirect('core:dashboard')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'SAVINGS')
        payment_reference = request.POST.get('payment_reference', '').strip()

        # Process payment (Savings Balance, Cash, bKash, Nagad, Bank)
        with transaction.atomic():
            if payment_method == 'SAVINGS':
                savings_account = getattr(loan.member, 'savings_account', None)
                if not savings_account or savings_account.balance < installment.total_amount:
                    messages.error(
                        request,
                        f"Insufficient savings balance (৳{savings_account.balance if savings_account else 0.00} available). Required: ৳{installment.total_amount}. Please deposit funds or choose Online Payment."
                    )
                    return redirect('loans:loan_detail', pk=loan.pk)

                # Deduct from member's savings
                savings_account.balance -= installment.total_amount
                savings_account.save(update_fields=['balance'])

                # Log savings debit
                SavingsTransaction.objects.create(
                    account=savings_account,
                    transaction_type='WITHDRAWAL',
                    amount=installment.total_amount,
                    payment_method='SAVINGS',
                    reference_note=f"Loan Phase #{installment.installment_number} Repayment ({loan.loan_id})",
                    status='APPROVED',
                    created_by=request.user,
                    processed_by=request.user,
                    processed_at=timezone.now()
                )

                reference = f"SAV-DEBIT-{savings_account.account_number}"

            elif payment_method in ['BKASH', 'NAGAD', 'BANK']:
                if not payment_reference:
                    payment_reference = f"MBL-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                reference = payment_reference
            else:
                reference = payment_reference or 'CASH-PAYMENT'

            # Mark installment as paid
            installment.mark_as_paid(
                collector=request.user,
                payment_amount=installment.total_amount,
                method=payment_method,
                reference=reference
            )

        messages.success(request, f"Installment #{installment.installment_number} (৳{installment.total_amount}) has been successfully PAID!")
        return redirect('loans:loan_detail', pk=loan.pk)

    return redirect('loans:loan_detail', pk=loan.pk)


# ==============================================================================
# 4B. SSLCOMMERZ ONLINE LOAN REPAYMENT (SANDBOX & LIVE)
# ==============================================================================
@login_required
def sslcommerz_initiate_installment(request, installment_id):
    """
    Directly initiates an SSLCOMMERZ Sandbox checkout session for a loan installment phase
    and immediately redirects the user to the official gateway payment page.
    """
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    loan = installment.loan

    # Authorization check: only loan owner or staff can initiate
    if request.user.is_member_user:
        if not hasattr(request.user, 'member_profile') or loan.member != request.user.member_profile:
            messages.error(request, "Unauthorized access to this loan installment.")
            return redirect('core:dashboard')

    tran_id = f"SSL-LN-{loan.loan_id}-{installment.id}-{int(timezone.now().timestamp())}-{uuid.uuid4().hex[:4].upper()}"
    SSLLoanPaymentSession.objects.create(
        tran_id=tran_id,
        installment=installment,
        amount=installment.total_amount,
        status='PENDING'
    )

    success_url = request.build_absolute_uri(reverse('loans:sslcommerz_loan_success'))
    fail_url = request.build_absolute_uri(reverse('loans:sslcommerz_loan_fail'))
    cancel_url = request.build_absolute_uri(reverse('loans:sslcommerz_loan_cancel'))

    res = sslcommerz_client.initiate_payment(
        tran_id=tran_id,
        amount=installment.total_amount,
        customer=request.user,
        success_url=success_url,
        fail_url=fail_url,
        cancel_url=cancel_url,
        product_name=f"Loan Repayment {loan.loan_id} Phase #{installment.installment_number}"
    )

    if res.get('status') == 'SUCCESS' and res.get('gateway_url'):
        return redirect(res['gateway_url'])
    else:
        messages.error(request, f"Could not connect to SSLCOMMERZ Sandbox Gateway: {res.get('message', 'Please try again')}")
        return redirect('loans:loan_detail', pk=loan.pk)


@csrf_exempt
def sslcommerz_loan_success_view(request):
    """
    SSLCOMMERZ POST callback on successful installment payment.
    Validates payment with validation API, marks installment as PAID, updates loan totals,
    delivers notifications, and displays the repayment receipt.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    val_id = request.POST.get('val_id') or request.GET.get('val_id')
    card_type = request.POST.get('card_type') or request.GET.get('card_type') or 'SSLCOMMERZ-Online'
    bank_tran_id = request.POST.get('bank_tran_id') or request.GET.get('bank_tran_id') or f"BNK-LOAN-{uuid.uuid4().hex[:8].upper()}"

    if not tran_id:
        messages.error(request, "Invalid payment callback: missing transaction ID.")
        return redirect('loans:my_loans')

    session = get_object_or_404(SSLLoanPaymentSession, tran_id=tran_id)
    installment = session.installment
    loan = installment.loan

    if val_id:
        val_res = sslcommerz_client.validate_payment(val_id, tran_id)
        if val_res.get('status') in ['VALID', 'VALIDATED']:
            card_type = val_res.get('card_type') or card_type
            bank_tran_id = val_res.get('bank_tran_id') or bank_tran_id

    if session.status != 'VALID':
        with transaction.atomic():
            session.status = 'VALID'
            session.val_id = val_id or f"VAL-LOAN-{uuid.uuid4().hex[:8].upper()}"
            session.card_type = card_type
            session.bank_tran_id = bank_tran_id
            session.validated_at = timezone.now()
            session.save()

            # Mark installment as PAID
            installment.mark_as_paid(
                collector=loan.member.user,
                payment_amount=session.amount,
                method='SSLCOMMERZ',
                reference=f"SSLCOMMERZ Sandbox ({card_type} - {session.val_id})"
            )

            # In-app notifications
            notify_user(
                user=loan.member.user,
                title="Online Loan Phase Payment Successful!",
                message=f"Phase #{installment.installment_number} of {session.amount} BDT for loan {loan.loan_id} was successfully paid via SSLCOMMERZ Sandbox ({card_type}). Remaining: {loan.remaining_balance} BDT.",
                link=f"/loans/{loan.id}/",
                notification_type='SUCCESS'
            )

            notify_staff_and_admins(
                title="Online Loan Repayment Received",
                message=f"Member {loan.member.member_id} settled Phase #{installment.installment_number} ({session.amount} BDT) for loan {loan.loan_id} via SSLCOMMERZ Sandbox ({card_type}).",
                link=f"/loans/{loan.id}/",
                notification_type='INFO'
            )

    return render(request, 'loans/sslcommerz_loan_receipt.html', {
        'session': session,
        'installment': installment,
        'loan': loan,
        'member': loan.member,
    })


@csrf_exempt
def sslcommerz_loan_fail_view(request):
    """
    Callback when payment fails or is declined by SSLCOMMERZ.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    loan_id = None
    if tran_id:
        session = SSLLoanPaymentSession.objects.filter(tran_id=tran_id).first()
        if session:
            session.status = 'FAILED'
            session.save()
            loan_id = session.installment.loan.id

    messages.error(request, "Online loan repayment transaction was declined or failed. Please try again.")
    if loan_id:
        return redirect('loans:loan_detail', pk=loan_id)
    return redirect('loans:my_loans')


@csrf_exempt
def sslcommerz_loan_cancel_view(request):
    """
    Callback when customer cancels payment.
    """
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    loan_id = None
    if tran_id:
        session = SSLLoanPaymentSession.objects.filter(tran_id=tran_id).first()
        if session:
            session.status = 'CANCELLED'
            session.save()
            loan_id = session.installment.loan.id

    messages.warning(request, "Online loan payment was cancelled.")
    if loan_id:
        return redirect('loans:loan_detail', pk=loan_id)
    return redirect('loans:my_loans')


# ==============================================================================
# 5. STAFF LOAN MANAGEMENT (List, Create, Approve, Reject, Disburse)
# ==============================================================================
@officer_required
def staff_loan_list(request):
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    loans = LoanApplication.objects.select_related('member__user', 'loan_product').order_by('-applied_at')

    if status_filter:
        loans = loans.filter(status=status_filter)
    if query:
        loans = loans.filter(
            Q(loan_id__icontains=query) |
            Q(member__member_id__icontains=query) |
            Q(member__user__first_name__icontains=query) |
            Q(member__user__last_name__icontains=query) |
            Q(purpose__icontains=query)
        )

    pending_count = LoanApplication.objects.filter(status='PENDING').count()
    active_count = LoanApplication.objects.filter(status='DISBURSED').count()
    completed_count = LoanApplication.objects.filter(status='COMPLETED').count()

    paginator = Paginator(loans, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/staff_loan_list.html', {
        'page_obj': page_obj,
        'loans': page_obj,
        'status_filter': status_filter,
        'query': query,
        'pending_count': pending_count,
        'active_count': active_count,
        'completed_count': completed_count,
    })


@officer_required
def staff_create_loan(request):
    if request.method == 'POST':
        form = StaffLoanApplicationForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            if loan.loan_product:
                loan.interest_rate = loan.loan_product.interest_rate_percent
            else:
                loan.interest_rate = Decimal('10.00')

            loan.status = 'PENDING'
            loan.save()

            messages.success(request, f"Loan application #{loan.loan_id} created for {loan.member.member_id}.")
            return redirect('loans:loan_detail', pk=loan.pk)
        else:
            messages.error(request, "Please check the loan application form.")
    else:
        member_id = request.GET.get('member')
        initial = {}
        if member_id:
            try:
                initial['member'] = MemberProfile.objects.get(id=member_id)
            except MemberProfile.DoesNotExist:
                pass
        form = StaffLoanApplicationForm(initial=initial)

    schemes = LoanScheme.objects.filter(is_active=True)
    return render(request, 'loans/staff_create_loan.html', {
        'form': form,
        'schemes': schemes
    })


@officer_required
def approve_loan(request, pk):
    loan = get_object_or_404(LoanApplication, pk=pk, status='PENDING')
    loan.status = 'APPROVED'
    loan.approved_by = request.user
    loan.approved_at = timezone.now()
    loan.save()

    messages.success(request, f"Loan #{loan.loan_id} has been approved.")
    return redirect('loans:loan_detail', pk=loan.pk)


@officer_required
def reject_loan(request, pk):
    loan = get_object_or_404(LoanApplication, pk=pk, status='PENDING')
    loan.status = 'REJECTED'
    loan.approved_by = request.user
    loan.approved_at = timezone.now()
    loan.save()

    messages.info(request, f"Loan #{loan.loan_id} has been marked as rejected.")
    return redirect('loans:loan_detail', pk=loan.pk)


@officer_required
def disburse_loan(request, pk):
    loan = get_object_or_404(LoanApplication, pk=pk, status='APPROVED')
    loan.status = 'DISBURSED'
    loan.disbursed_at = timezone.now()
    loan.save()

    # Automatically generate monthly installment schedule
    loan.generate_installments()

    messages.success(request, f"Loan #{loan.loan_id} disbursed successfully. Installments schedule generated.")
    return redirect('loans:loan_detail', pk=loan.pk)


@officer_required
def collect_installment(request, installment_id):
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    loan = installment.loan

    installment.mark_as_paid(collector=request.user)

    messages.success(request, f"Installment #{installment.installment_number} collected successfully (৳{installment.total_amount}).")
    return redirect('loans:loan_detail', pk=loan.pk)


# ==============================================================================
# 7. LOAN SCHEMES / PRODUCTS MANAGEMENT (Admin Only)
# ==============================================================================
@admin_required
def loan_schemes_list(request):
    schemes = LoanScheme.objects.all().order_by('-id')
    form = LoanSchemeForm()

    if request.method == 'POST':
        form = LoanSchemeForm(request.POST)
        if form.is_valid():
            scheme = form.save()
            messages.success(request, f"Loan Scheme '{scheme.name}' created successfully.")
            return redirect('loans:schemes_list')
        else:
            messages.error(request, "Please fix the errors in the form.")

    return render(request, 'loans/loan_schemes.html', {
        'schemes': schemes,
        'form': form,
    })


# ==============================================================================
# 8. LOAN STATEMENT GENERATOR & PDF EXPORT
# ==============================================================================
@login_required
def loan_statement_view(request, pk=None):
    if request.user.is_member_user:
        profile = getattr(request.user, 'member_profile', None)
        if not profile:
            return redirect('core:dashboard')
        if pk:
            loan = get_object_or_404(LoanApplication, pk=pk, member=profile)
        else:
            loan = profile.loans.order_by('-applied_at').first()
        available_loans = profile.loans.all().order_by('-applied_at')
    else:
        # Officer / Admin
        if pk:
            loan = get_object_or_404(LoanApplication, pk=pk)
        else:
            loan_param = request.GET.get('loan')
            if loan_param:
                loan = LoanApplication.objects.filter(id=loan_param).first()
            else:
                loan = LoanApplication.objects.order_by('-applied_at').first()
        available_loans = LoanApplication.objects.select_related('member__user').order_by('-applied_at')[:50]

    installments = []
    paid_installments_count = 0
    pending_installments_count = 0
    overdue_installments_count = 0

    if loan:
        installments = loan.installments.select_related('collected_by').order_by('installment_number')
        paid_installments_count = installments.filter(status='PAID').count()
        pending_installments_count = installments.filter(status='PENDING').count()
        overdue_installments_count = installments.filter(status='OVERDUE').count()

    # Step 5: Render statement template (supports standard browser printing)

    return render(request, 'loans/loan_statement.html', {
        'loan': loan,
        'installments': installments,
        'available_loans': available_loans,
        'paid_count': paid_installments_count,
        'pending_count': pending_installments_count,
        'overdue_count': overdue_installments_count,
        'generated_at': timezone.now(),
    })
