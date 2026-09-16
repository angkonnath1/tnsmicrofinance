import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.views.decorators.csrf import csrf_exempt

from apps.accounts.decorators import officer_required, member_required, admin_required
from apps.members.models import MemberProfile
from apps.savings.models import SavingsTransaction
from apps.core.sslcommerz import sslcommerz_client
from apps.notifications.utils import notify_user, notify_staff_and_admins
from apps.core.utils import paginate
from .models import LoanApplication, LoanInstallment, LoanScheme, SSLLoanPaymentSession
from .forms import MemberLoanApplicationForm, StaffLoanApplicationForm, LoanSchemeForm


def _save_loan(loan, product):
    loan.interest_rate = product.interest_rate_percent if product else Decimal('10.00')
    loan.status = 'PENDING'
    loan.save()
    return loan


# ==============================================================================
# 1. MEMBER LOANS & APPLICATION
# ==============================================================================

@member_required
def my_loans_view(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        return redirect('core:dashboard')

    loans = profile.loans.select_related('loan_product').order_by('-applied_at')
    page_obj = paginate(request, loans, 10)

    loan_totals = loans.aggregate(
        borrowed=Sum('principal_amount', filter=Q(status__in=['DISBURSED', 'COMPLETED'])),
        repaid=Sum('total_paid'),
    )

    return render(request, 'loans/my_loans.html', {
        'page_obj': page_obj,
        'loans': page_obj,
        'active_loans': loans.filter(status='DISBURSED'),
        'pending_loans': loans.filter(status='PENDING'),
        'completed_loans': loans.filter(status='COMPLETED'),
        'total_borrowed': loan_totals['borrowed'] or 0,
        'total_repaid': loan_totals['repaid'] or 0,
    })


@member_required
def apply_loan_view(request):
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        messages.error(request, "Please complete your member profile first.")
        return redirect('core:dashboard')

    if profile.loans.filter(status__in=['PENDING', 'APPROVED']).exists():
        messages.warning(request, "You already have a loan application in progress.")
        return redirect('loans:my_loans')

    if request.method == 'POST':
        form = MemberLoanApplicationForm(request.POST, applicant_member=profile)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.member = profile
            _save_loan(loan, loan.loan_product)
            messages.success(request, f"Loan application #{loan.loan_id} for ৳{loan.principal_amount} submitted successfully!")
            return redirect('loans:loan_detail', pk=loan.pk)
        messages.error(request, "Please check the form for errors.")
    else:
        scheme = LoanScheme.objects.filter(id=request.GET.get('scheme'), is_active=True).first()
        initial = {
            'loan_product': scheme,
            'principal_amount': scheme.min_amount,
            'duration_months': scheme.duration_months,
            'installment_frequency': scheme.installment_frequency,
        } if scheme else {}
        form = MemberLoanApplicationForm(initial=initial, applicant_member=profile)

    return render(request, 'loans/apply_loan.html', {
        'form': form,
        'schemes': LoanScheme.objects.filter(is_active=True),
    })


@login_required
def loan_detail_view(request, pk):
    loan = get_object_or_404(
        LoanApplication.objects.select_related('member__user', 'loan_product', 'approved_by'),
        pk=pk
    )
    if request.user.is_member_user and getattr(request.user, 'member_profile', None) != loan.member:
        messages.error(request, "Access restricted.")
        return redirect('core:dashboard')

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'installments': loan.installments.select_related('collected_by').order_by('installment_number'),
        'savings_account': getattr(loan.member, 'savings_account', None),
    })


# ==============================================================================
# 2. INSTALLMENT PAYMENT (SAVINGS, CASH, MFS, SSLCOMMERZ)
# ==============================================================================

@login_required
def member_pay_installment(request, installment_id):
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    loan = installment.loan

    if request.user.is_member_user and getattr(request.user, 'member_profile', None) != loan.member:
        messages.error(request, "Unauthorized access to this loan installment.")
        return redirect('core:dashboard')

    if request.method == 'POST':
        method = request.POST.get('payment_method', 'SAVINGS')
        ref = request.POST.get('payment_reference', '').strip()

        with transaction.atomic():
            if method == 'SAVINGS':
                savings = getattr(loan.member, 'savings_account', None)
                if not savings or savings.balance < installment.total_amount:
                    avail = savings.balance if savings else 0
                    messages.error(request, f"Insufficient savings balance (৳{avail} available). Required: ৳{installment.total_amount}.")
                    return redirect('loans:loan_detail', pk=loan.pk)

                savings.balance -= installment.total_amount
                savings.save(update_fields=['balance'])

                SavingsTransaction.objects.create(
                    account=savings,
                    transaction_type='WITHDRAWAL',
                    amount=installment.total_amount,
                    payment_method='SAVINGS',
                    reference_note=f"Loan Phase #{installment.installment_number} Repayment ({loan.loan_id})",
                    status='APPROVED',
                    created_by=request.user,
                    processed_by=request.user,
                    processed_at=timezone.now()
                )
                ref = f"SAV-DEBIT-{savings.account_number}"
            elif method in ['BKASH', 'NAGAD', 'BANK']:
                ref = ref or f"MBL-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            else:
                ref = ref or 'CASH-PAYMENT'

            installment.mark_as_paid(collector=request.user, payment_amount=installment.total_amount, method=method, reference=ref)

        messages.success(request, f"Installment #{installment.installment_number} (৳{installment.total_amount}) has been successfully PAID!")
    return redirect('loans:loan_detail', pk=loan.pk)


@login_required
def sslcommerz_initiate_installment(request, installment_id):
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    loan = installment.loan

    if request.user.is_member_user and getattr(request.user, 'member_profile', None) != loan.member:
        messages.error(request, "Unauthorized access.")
        return redirect('core:dashboard')

    tran_id = f"SSL-LN-{loan.loan_id}-{installment.id}-{int(timezone.now().timestamp())}-{uuid.uuid4().hex[:4].upper()}"
    SSLLoanPaymentSession.objects.create(tran_id=tran_id, installment=installment, amount=installment.total_amount, status='PENDING')

    res = sslcommerz_client.initiate_payment(
        tran_id=tran_id,
        amount=installment.total_amount,
        customer=request.user,
        success_url=request.build_absolute_uri(reverse('loans:sslcommerz_loan_success')),
        fail_url=request.build_absolute_uri(reverse('loans:sslcommerz_loan_fail')),
        cancel_url=request.build_absolute_uri(reverse('loans:sslcommerz_loan_cancel')),
        product_name=f"Loan Repayment {loan.loan_id} Phase #{installment.installment_number}"
    )

    if res.get('status') == 'SUCCESS' and res.get('gateway_url'):
        return redirect(res['gateway_url'])
    messages.error(request, f"Could not connect to payment gateway: {res.get('message', 'Please try again')}")
    return redirect('loans:loan_detail', pk=loan.pk)


@csrf_exempt
def sslcommerz_loan_success_view(request):
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    if not tran_id:
        messages.error(request, "Invalid payment callback: missing transaction ID.")
        return redirect('loans:my_loans')

    session = get_object_or_404(SSLLoanPaymentSession, tran_id=tran_id)
    installment, loan = session.installment, session.installment.loan
    val_id = request.POST.get('val_id') or request.GET.get('val_id')
    card_type = request.POST.get('card_type') or request.GET.get('card_type') or 'SSLCOMMERZ-Online'
    bank_tran_id = request.POST.get('bank_tran_id') or request.GET.get('bank_tran_id') or f"BNK-LOAN-{uuid.uuid4().hex[:8].upper()}"

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

            installment.mark_as_paid(
                collector=loan.member.user,
                payment_amount=session.amount,
                method='SSLCOMMERZ',
                reference=f"SSLCOMMERZ Sandbox ({card_type} - {session.val_id})"
            )
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


def _handle_ssl_result(request, status, msg, is_error=True):
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    loan_id = None
    if tran_id:
        session = SSLLoanPaymentSession.objects.filter(tran_id=tran_id).first()
        if session:
            session.status = status
            session.save()
            loan_id = session.installment.loan_id
    (messages.error if is_error else messages.warning)(request, msg)
    return redirect('loans:loan_detail', pk=loan_id) if loan_id else redirect('loans:my_loans')


@csrf_exempt
def sslcommerz_loan_fail_view(request):
    return _handle_ssl_result(request, 'FAILED', "Online loan repayment transaction was declined or failed. Please try again.", is_error=True)


@csrf_exempt
def sslcommerz_loan_cancel_view(request):
    return _handle_ssl_result(request, 'CANCELLED', "Online loan payment was cancelled.", is_error=False)


# ==============================================================================
# 3. STAFF LOAN OPERATIONS & APPROVALS
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

    counts = LoanApplication.objects.aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        active=Count('id', filter=Q(status='DISBURSED')),
        completed=Count('id', filter=Q(status='COMPLETED')),
    )

    page_obj = paginate(request, loans, 15)
    return render(request, 'loans/staff_loan_list.html', {
        'page_obj': page_obj,
        'loans': page_obj,
        'status_filter': status_filter,
        'query': query,
        'pending_count': counts['pending'],
        'active_count': counts['active'],
        'completed_count': counts['completed'],
    })


@officer_required
def staff_create_loan(request):
    if request.method == 'POST':
        form = StaffLoanApplicationForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            _save_loan(loan, loan.loan_product)
            messages.success(request, f"Loan application #{loan.loan_id} created for {loan.member.member_id}.")
            return redirect('loans:loan_detail', pk=loan.pk)
        messages.error(request, "Please check the loan application form.")
    else:
        member = MemberProfile.objects.filter(id=request.GET.get('member')).first()
        form = StaffLoanApplicationForm(initial={'member': member} if member else {})

    return render(request, 'loans/staff_create_loan.html', {
        'form': form,
        'schemes': LoanScheme.objects.filter(is_active=True),
    })


def _update_loan_review(request, pk, status, msg):
    loan = get_object_or_404(LoanApplication, pk=pk, status='PENDING')
    loan.status = status
    loan.approved_by = request.user
    loan.approved_at = timezone.now()
    loan.save()
    messages.success(request, msg.format(loan_id=loan.loan_id))
    return redirect('loans:loan_detail', pk=loan.pk)


@officer_required
def approve_loan(request, pk):
    return _update_loan_review(request, pk, 'APPROVED', "Loan #{loan_id} has been approved.")


@officer_required
def reject_loan(request, pk):
    return _update_loan_review(request, pk, 'REJECTED', "Loan #{loan_id} has been marked as rejected.")


@officer_required
def disburse_loan(request, pk):
    loan = get_object_or_404(LoanApplication, pk=pk, status='APPROVED')
    loan.status = 'DISBURSED'
    loan.disbursed_at = timezone.now()
    loan.save()
    loan.generate_installments()
    messages.success(request, f"Loan #{loan.loan_id} disbursed successfully. Installments schedule generated.")
    return redirect('loans:loan_detail', pk=loan.pk)


@officer_required
def collect_installment(request, installment_id):
    installment = get_object_or_404(LoanInstallment, id=installment_id, status__in=['PENDING', 'OVERDUE'])
    installment.mark_as_paid(collector=request.user)
    messages.success(request, f"Installment #{installment.installment_number} collected successfully (৳{installment.total_amount}).")
    return redirect('loans:loan_detail', pk=installment.loan_id)


# ==============================================================================
# 4. SCHEMES & STATEMENTS
# ==============================================================================

@admin_required
def loan_schemes_list(request):
    form = LoanSchemeForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            scheme = form.save()
            messages.success(request, f"Loan Scheme '{scheme.name}' created successfully.")
            return redirect('loans:schemes_list')
        messages.error(request, "Please fix the errors in the form.")

    return render(request, 'loans/loan_schemes.html', {
        'schemes': LoanScheme.objects.all().order_by('-id'),
        'form': form,
    })


@login_required
def loan_statement_view(request, pk=None):
    if request.user.is_member_user:
        profile = getattr(request.user, 'member_profile', None)
        if not profile:
            return redirect('core:dashboard')
        loan = get_object_or_404(LoanApplication, pk=pk, member=profile) if pk else profile.loans.order_by('-applied_at').first()
        available_loans = profile.loans.all().order_by('-applied_at')
    else:
        if pk:
            loan = get_object_or_404(LoanApplication, pk=pk)
        else:
            loan_param = request.GET.get('loan')
            loan = LoanApplication.objects.filter(id=loan_param).first() if loan_param else LoanApplication.objects.order_by('-applied_at').first()
        available_loans = LoanApplication.objects.select_related('member__user').order_by('-applied_at')[:50]

    counts = {'paid': 0, 'pending': 0, 'overdue': 0}
    installments = []
    if loan:
        installments = loan.installments.select_related('collected_by').order_by('installment_number')
        inst_counts = installments.aggregate(
            paid=Count('id', filter=Q(status='PAID')),
            pending=Count('id', filter=Q(status='PENDING')),
            overdue=Count('id', filter=Q(status='OVERDUE')),
        )
        counts.update(inst_counts)

    return render(request, 'loans/loan_statement.html', {
        'loan': loan,
        'installments': installments,
        'available_loans': available_loans,
        'paid_count': counts['paid'],
        'pending_count': counts['pending'],
        'overdue_count': counts['overdue'],
        'generated_at': timezone.now(),
    })
