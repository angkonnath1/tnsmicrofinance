from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import CustomUser
from .forms import LoginForm, OfficerCreationForm, UserProfileForm
from .decorators import admin_required
from apps.members.forms import MemberSelfRegistrationForm
from apps.savings.models import SavingsAccount
from apps.core.utils import paginate


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(request.GET.get('next') or 'core:dashboard')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = MemberSelfRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data.get('email', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    role='MEMBER',
                    password=form.cleaned_data['password'],
                    is_active=False
                )
                if 'member_photo' in request.FILES:
                    user.profile_picture = request.FILES['member_photo']
                    user.save(update_fields=['profile_picture'])

                profile = form.save(commit=False)
                profile.user = user
                profile.status = 'PENDING'
                profile.save()

                SavingsAccount.objects.create(
                    member=profile,
                    account_number=f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"
                )

                request.session['registration_info'] = {
                    'name': user.get_full_name() or user.username,
                    'member_id': profile.member_id,
                    'username': user.username,
                    'phone': user.phone or 'N/A'
                }
                return redirect('accounts:registration_submitted')
        messages.error(request, "Please correct the errors below in the registration form.")
    else:
        form = MemberSelfRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def registration_submitted_view(request):
    info = request.session.get('registration_info', {
        'name': 'Valued Member',
        'member_id': 'TNS-MEM-PENDING',
        'username': 'Your account',
        'phone': ''
    })
    return render(request, 'accounts/registration_submitted.html', {'info': info})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile = getattr(request.user, 'member_profile', None)
    if request.user.is_member_user or profile is not None:
        return render(request, 'accounts/profile.html', {'profile': profile})

    assigned_members = request.user.assigned_members.select_related('user').order_by('-joined_date') if request.user.is_officer_user else []
    active_loans_count = 0
    if request.user.is_officer_user:
        from apps.loans.models import LoanApplication
        active_loans_count = LoanApplication.objects.filter(
            member__assigned_officer=request.user, status='DISBURSED'
        ).count()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': None,
        'assigned_members': assigned_members,
        'assigned_members_count': len(assigned_members) if isinstance(assigned_members, list) else assigned_members.count(),
        'active_loans_count': active_loans_count,
    })


@admin_required
def officer_list_view(request):
    if request.method == 'POST':
        form = OfficerCreationForm(request.POST)
        if form.is_valid():
            officer = form.save()
            messages.success(request, f"Officer account '{officer.username}' created successfully.")
            return redirect('accounts:officer_list')
        messages.error(request, "Please fix the errors in the form.")
    else:
        form = OfficerCreationForm()

    officers = CustomUser.objects.filter(role='OFFICER').order_by('-date_joined')
    page_obj = paginate(request, officers, 10)

    return render(request, 'accounts/officer_list.html', {
        'page_obj': page_obj,
        'officers': page_obj,
        'form': form,
    })


@admin_required
def officer_toggle_status(request, user_id):
    officer = get_object_or_404(CustomUser, id=user_id, role='OFFICER')
    officer.is_active = not officer.is_active
    officer.save()
    status = "activated" if officer.is_active else "deactivated"
    messages.success(request, f"Officer {officer.username} has been {status}.")
    return redirect('accounts:officer_list')
