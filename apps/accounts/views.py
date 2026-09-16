"""
==============================================================================
Touch and Solve Microfinance - Accounts App Views
Author: Beginner Learner Developer / Learning Project
Description: Views for handling user authentication (Login, Register, Logout),
             user profile views, and managing Field Officers.
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator

# Import account models, forms, and custom decorators
from .models import CustomUser
from .forms import LoginForm, OfficerCreationForm, UserProfileForm
from .decorators import admin_required
from apps.members.forms import MemberSelfRegistrationForm
from apps.members.models import MemberProfile
from apps.savings.models import SavingsAccount


# ==============================================================================
# 1. USER LOGIN VIEW
# Handles user authentication and redirects them to the right dashboard.
# ==============================================================================
def login_view(request):
    # If the user is already logged in, send them straight to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    # When the user submits the login form (HTTP POST)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Retrieve authenticated user from form cleaned_data
            user = form.cleaned_data['user']
            login(request, user) # Creates the session in Django
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            
            # Check if there was a 'next' URL parameter, otherwise go to dashboard
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('core:dashboard')
    else:
        # For HTTP GET request, display an empty login form
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# ==============================================================================
# 2. MEMBER SELF REGISTRATION VIEW
# Allows new members to register an account online with KYC verification documents.
# ==============================================================================
def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = MemberSelfRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Use database transaction so all records are saved together safely
            with transaction.atomic():
                # Step 1: Create the User account (set is_active=False until approved by officer)
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

                # Step 2: Save profile picture if uploaded
                if 'member_photo' in request.FILES:
                    user.profile_picture = request.FILES['member_photo']
                    user.save(update_fields=['profile_picture'])

                # Step 3: Create MemberProfile record with PENDING status
                profile = form.save(commit=False)
                profile.user = user
                profile.status = 'PENDING'
                profile.save()

                # Step 4: Create a default savings account for the new member
                SavingsAccount.objects.create(
                    member=profile,
                    account_number=f"SAV-{profile.member_id.replace('TNS-MEM-', '')}"
                )

                # Step 5: Store basic registration summary in session for confirmation screen
                request.session['registration_info'] = {
                    'name': user.get_full_name() or user.username,
                    'member_id': profile.member_id,
                    'username': user.username,
                    'phone': user.phone or 'N/A'
                }
                return redirect('accounts:registration_submitted')
        else:
            messages.error(request, "Please correct the errors below in the registration form.")
    else:
        form = MemberSelfRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ==============================================================================
# 3. REGISTRATION SUBMITTED CONFIRMATION VIEW
# Displays confirmation message and application number to the applicant.
# ==============================================================================
def registration_submitted_view(request):
    registration_info = request.session.get('registration_info', {
        'name': 'Valued Member',
        'member_id': 'TNS-MEM-PENDING',
        'username': 'Your account',
        'phone': ''
    })
    return render(request, 'accounts/registration_submitted.html', {
        'info': registration_info
    })


# ==============================================================================
# 4. USER LOGOUT VIEW
# Clears user session and logs out.
# ==============================================================================
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')


# ==============================================================================
# 5. USER PROFILE VIEW
# Allows logged-in user to view their profile.
# For Members: displays complete personal and nominee KYC records (strictly read-only).
# For Staff/Officers: allows editing basic administrative account details.
# ==============================================================================
@login_required
def profile_view(request):
    profile = getattr(request.user, 'member_profile', None)

    # Members cannot edit their profile; it is strictly read-only official KYC information
    if request.user.is_member_user or profile is not None:
        return render(request, 'accounts/profile.html', {
            'profile': profile,
        })

    # Staff / Officer profile management
    assigned_members = MemberProfile.objects.none()
    active_loans_count = 0
    if request.user.is_officer_user:
        assigned_members = request.user.assigned_members.select_related('user').order_by('-joined_date')
        from apps.loans.models import LoanApplication
        active_loans_count = LoanApplication.objects.filter(
            member__assigned_officer=request.user,
            status='DISBURSED'
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
        'assigned_members_count': assigned_members.count(),
        'active_loans_count': active_loans_count,
    })


# ==============================================================================
# 6. OFFICER MANAGEMENT LIST VIEW (Admin Only)
# Admin view to list all Field Officers and create new officer accounts.
# ==============================================================================
@admin_required
def officer_list_view(request):
    officers = CustomUser.objects.filter(role='OFFICER').order_by('-date_joined')
    form = OfficerCreationForm()
    
    # Handle creation of a new officer account
    if request.method == 'POST':
        form = OfficerCreationForm(request.POST)
        if form.is_valid():
            officer = form.save()
            messages.success(request, f"Officer account for '{officer.username}' created successfully.")
            return redirect('accounts:officer_list')
        else:
            messages.error(request, "Please fix the errors in the form.")

    # Paginate results (10 officers per page)
    paginator = Paginator(officers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/officer_list.html', {
        'page_obj': page_obj,
        'officers': page_obj,
        'form': form,
    })


# ==============================================================================
# 7. TOGGLE OFFICER STATUS (Active / Inactive)
# ==============================================================================
@admin_required
def officer_toggle_status(request, user_id):
    officer = get_object_or_404(CustomUser, id=user_id, role='OFFICER')
    officer.is_active = not officer.is_active
    officer.save()
    status_text = "activated" if officer.is_active else "deactivated"
    messages.success(request, f"Officer {officer.username} has been {status_text}.")
    return redirect('accounts:officer_list')
