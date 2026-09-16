from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.decorators import officer_required
from apps.savings.models import SavingsAccount
from apps.core.utils import paginate
from .models import MemberProfile
from .forms import MemberRegistrationForm, MemberProfileEditForm


@officer_required
def member_list_view(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    members = MemberProfile.objects.select_related('user', 'assigned_officer').order_by('-joined_date')

    if query:
        q_obj = Q()
        for term in query.split():
            q_obj &= (
                Q(member_id__icontains=term) |
                Q(user__first_name__icontains=term) |
                Q(user__last_name__icontains=term) |
                Q(user__phone__icontains=term) |
                Q(user__username__icontains=term) |
                Q(nid_number__icontains=term)
            )
        members = members.filter(q_obj)

    if status_filter:
        members = members.filter(status=status_filter)

    page_obj = paginate(request, members, 10)
    return render(request, 'members/member_list.html', {
        'page_obj': page_obj,
        'members': page_obj,
        'query': query,
        'status_filter': status_filter,
    })


@officer_required
def member_create_view(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data.get('email', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    role='MEMBER',
                    password=form.cleaned_data['password']
                )
                if 'member_photo' in request.FILES:
                    user.profile_picture = request.FILES['member_photo']
                    user.save(update_fields=['profile_picture'])

                profile = form.save(commit=False)
                profile.user = user
                if not profile.assigned_officer and request.user.role == 'OFFICER':
                    profile.assigned_officer = request.user
                profile.save()

                acc_num = f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"
                counter = 1
                base_acc = acc_num
                while SavingsAccount.objects.filter(account_number=acc_num).exists():
                    acc_num = f"{base_acc}-{counter}"
                    counter += 1
                SavingsAccount.objects.create(member=profile, account_number=acc_num)

            messages.success(request, f"Member '{profile.member_id} - {user.get_full_name()}' registered successfully!")
            return redirect('members:member_detail', pk=profile.pk)
        messages.error(request, "Please check the form for errors.")
    else:
        form = MemberRegistrationForm()

    return render(request, 'members/member_create.html', {'form': form})


@login_required
def member_detail_view(request, pk):
    profile = get_object_or_404(MemberProfile.objects.select_related('user', 'assigned_officer'), pk=pk)

    if request.user.is_member_user and getattr(request.user, 'member_profile', None) != profile:
        messages.error(request, "Access restricted.")
        return redirect('core:dashboard')

    savings_account = getattr(profile, 'savings_account', None)
    return render(request, 'members/member_detail.html', {
        'profile': profile,
        'savings_account': savings_account,
        'savings_transactions': savings_account.transactions.select_related('processed_by').order_by('-created_at')[:10] if savings_account else [],
        'loans': profile.loans.order_by('-applied_at'),
    })


@officer_required
def member_edit_view(request, pk):
    profile = get_object_or_404(MemberProfile, pk=pk)
    user = profile.user

    if request.method == 'POST':
        form = MemberProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data.get('email', '')
            user.phone = form.cleaned_data['phone']
            if 'member_photo' in request.FILES:
                user.profile_picture = request.FILES['member_photo']
            user.save()
            form.save()
            messages.success(request, f"Profile for {profile.member_id} updated successfully.")
            return redirect('members:member_detail', pk=profile.pk)
    else:
        form = MemberProfileEditForm(instance=profile, initial={
            'first_name': user.first_name, 'last_name': user.last_name,
            'email': user.email, 'phone': user.phone,
        })

    return render(request, 'members/member_edit.html', {'form': form, 'profile': profile})


def _set_member_status(request, pk, status, is_active, reason=None, msg="", is_warning=False):
    profile = get_object_or_404(MemberProfile, pk=pk)
    with transaction.atomic():
        profile.status = status
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.rejection_reason = reason
        profile.save()
        profile.user.is_active = is_active
        profile.user.save(update_fields=['is_active'])

    (messages.warning if is_warning else messages.success)(request, msg.format(member_id=profile.member_id, name=profile.user.get_full_name()))
    return redirect('members:member_detail', pk=profile.pk)


@officer_required
def member_approve_view(request, pk):
    return _set_member_status(request, pk, 'ACTIVE', True, None, "Member {member_id} ({name}) has been APPROVED.")


@officer_required
def member_reject_view(request, pk):
    reason = request.POST.get('reason', 'KYC documentation could not be verified.')
    return _set_member_status(request, pk, 'REJECTED', False, reason, "Member application {member_id} has been marked as REJECTED.", is_warning=True)
