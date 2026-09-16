"""
==============================================================================
Touch and Solve Microfinance - Members App Views
Author: Beginner Learner Developer / Learning Project
Description: Views for searching, registering, viewing, approving,
             and rejecting co-operative member profiles.
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

# Import accounts and member models/forms
from apps.accounts.models import CustomUser
from apps.accounts.decorators import officer_required
from apps.savings.models import SavingsAccount
from .models import MemberProfile
from .forms import MemberRegistrationForm, MemberProfileEditForm


# ==============================================================================
# 1. MEMBER LIST VIEW (Search & Filter)
# Officers can search members by Name, ID, Phone, or NID number.
# ==============================================================================
@officer_required
def member_list_view(request):
    # Step 1: Read search query and status filter from GET parameters
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    # Step 2: Fetch all members from database ordered by registration date
    members = MemberProfile.objects.select_related('user', 'assigned_officer').order_by('-joined_date')

    # Step 3: Apply text search filter if query is provided
    if query:
        terms = query.split()
        q_obj = Q()
        for term in terms:
            q_obj &= (
                Q(member_id__icontains=term) |
                Q(user__first_name__icontains=term) |
                Q(user__last_name__icontains=term) |
                Q(user__phone__icontains=term) |
                Q(user__username__icontains=term) |
                Q(nid_number__icontains=term)
            )
        members = members.filter(q_obj)

    # Step 4: Apply status filter (ACTIVE, PENDING, REJECTED, etc.)
    if status_filter:
        members = members.filter(status=status_filter)

    # Step 5: Paginate 10 members per page
    paginator = Paginator(members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Step 6: Render member list template
    context = {
        'page_obj': page_obj,
        'members': page_obj,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'members/member_list.html', context)


# ==============================================================================
# 2. CREATE NEW MEMBER VIEW (Officer Enrolling a Member)
# Creates CustomUser, MemberProfile, and opening SavingsAccount in one transaction.
# ==============================================================================
@officer_required
def member_create_view(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                # Step 1: Create user record
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data.get('email', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    role='MEMBER',
                    password=form.cleaned_data['password']
                )

                # Step 2: Attach profile picture if uploaded
                if 'member_photo' in request.FILES:
                    user.profile_picture = request.FILES['member_photo']
                    user.save(update_fields=['profile_picture'])

                # Step 3: Create MemberProfile record
                profile = form.save(commit=False)
                profile.user = user
                if not profile.assigned_officer and request.user.role == 'OFFICER':
                    profile.assigned_officer = request.user
                profile.save()

                # Step 4: Automatically provision default Savings Account
                acc_num = f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"
                counter = 1
                base_acc = acc_num
                while SavingsAccount.objects.filter(account_number=acc_num).exists():
                    acc_num = f"{base_acc}-{counter}"
                    counter += 1
                SavingsAccount.objects.create(
                    member=profile,
                    account_number=acc_num
                )

            messages.success(request, f"Member '{profile.member_id} - {user.get_full_name()}' registered successfully!")
            return redirect('members:member_detail', pk=profile.pk)
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = MemberRegistrationForm()

    return render(request, 'members/member_create.html', {'form': form})


# ==============================================================================
# 3. MEMBER DETAIL VIEW
# Displays member profile card, KYC photo/NID, savings balance, and loan history.
# ==============================================================================
@login_required
def member_detail_view(request, pk):
    profile = get_object_or_404(MemberProfile.objects.select_related('user', 'assigned_officer'), pk=pk)

    # Permission check: A member can only view their own profile; Officers/Admins can view any
    if request.user.is_member_user and hasattr(request.user, 'member_profile') and request.user.member_profile.pk != profile.pk:
        messages.error(request, "Access restricted.")
        return redirect('core:dashboard')

    # Fetch savings account and recent 10 transactions
    savings_account = getattr(profile, 'savings_account', None)
    savings_transactions = []
    if savings_account:
        savings_transactions = savings_account.transactions.select_related('processed_by').order_by('-created_at')[:10]

    # Fetch all loans for this member
    loans = profile.loans.order_by('-applied_at')

    context = {
        'profile': profile,
        'savings_account': savings_account,
        'savings_transactions': savings_transactions,
        'loans': loans,
    }
    return render(request, 'members/member_detail.html', context)


# ==============================================================================
# 4. EDIT MEMBER PROFILE VIEW
# Allows Field Officers to update member personal details and nominee info.
# ==============================================================================
@officer_required
def member_edit_view(request, pk):
    profile = get_object_or_404(MemberProfile, pk=pk)
    user = profile.user

    if request.method == 'POST':
        form = MemberProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Update user model fields
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
        initial_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone,
        }
        form = MemberProfileEditForm(instance=profile, initial=initial_data)

    return render(request, 'members/member_edit.html', {
        'form': form,
        'profile': profile
    })


# ==============================================================================
# 5. APPROVE MEMBER APPLICATION VIEW
# Officer approves a pending member application and activates their account login.
# ==============================================================================
@officer_required
def member_approve_view(request, pk):
    profile = get_object_or_404(MemberProfile, pk=pk)
    
    with transaction.atomic():
        profile.status = 'ACTIVE'
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.rejection_reason = None
        profile.save()

        # Activate the user's login credentials
        profile.user.is_active = True
        profile.user.save(update_fields=['is_active'])

    messages.success(request, f"Member {profile.member_id} ({profile.user.get_full_name()}) has been APPROVED and activated.")
    return redirect('members:member_detail', pk=profile.pk)


# ==============================================================================
# 6. REJECT MEMBER APPLICATION VIEW
# Officer rejects an application with a specified reason.
# ==============================================================================
@officer_required
def member_reject_view(request, pk):
    profile = get_object_or_404(MemberProfile, pk=pk)
    reason = request.POST.get('reason', 'KYC documentation or requirements could not be verified.')

    with transaction.atomic():
        profile.status = 'REJECTED'
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.rejection_reason = reason
        profile.save()

        # Deactivate user login
        profile.user.is_active = False
        profile.user.save(update_fields=['is_active'])


    messages.warning(request, f"Member application {profile.member_id} has been marked as REJECTED.")
    return redirect('members:member_detail', pk=profile.pk)
