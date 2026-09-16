# TOUCH & SOLVE (TNS) MICROFINANCE CO-OPERATIVE MANAGEMENT SYSTEM
## Comprehensive Master System Specification & Implementation Blueprint

> **Purpose of this Document:**  
> This specification is an exhaustive, self-contained architectural and functional blueprint. Any AI agent, developer, or engineering team provided with this document will be able to construct, test, and deploy the entire Touch & Solve Microfinance system from scratch with zero ambiguity.

---

## 1. System Overview & Core Objectives

### 1.1 Mission & Vision
**Touch & Solve Microfinance Co-operative** is an enterprise-grade financial management web application built to digitize community banking, savings mobilization, micro-credit loan origination, and field collection operations.

### 1.2 Core Capabilities
1. **Three-Tier Role-Based Access Control (RBAC):** Admin (Executive), Field Officer (Staff), and Member (Borrower/Saver).
2. **Member KYC & Lifecycle Management:** Automated Member ID generation (`TNS-MEM-YYYY-XXXX`), document records, nominee details, and status workflow (`PENDING` -> `ACTIVE` / `REJECTED`).
3. **Savings Management System:** Auto-provisioned savings accounts (`SAV-XXXX`), manual deposit/withdrawal requests with officer approval workflows, running ledger balance calculation, and print-ready account statements.
4. **Loan Origination & Amortization Engine:** Flexible loan schemes (Weekly/Monthly), flat-rate interest calculations, automatic installment schedule generation, penalty tracking, guarantor validation, and statements.
5. **Multi-Channel Payment Processing:**
   - Cash collections recorded by field officers.
   - Internal savings account balance deduction to pay loan installments.
   - Mobile Financial Services (bKash, Nagad, Rocket).
   - **Official SSLCOMMERZ V4 Hosted Payment Gateway** (Sandbox & Live) with instant server-to-server transaction validation and automated ledger settlement.
6. **Executive Dashboards & Operational Reports:** Real-time collection sheets, daily master cash inflow/outflow reports, and financial health audits.
7. **In-App Real-Time Notification Center:** Context-aware event alerts with notification badges.

---

## 2. Technology Stack & Dependencies

- **Language:** Python 3.11+
- **Backend Framework:** Django 5.x (MTV - Model-Template-View Architecture)
- **Database:** SQLite for local development; PostgreSQL for production with `dj-database-url`
- **Frontend Architecture:** Django Templates + Semantic HTML5 + Custom Vanilla CSS (Design Tokens, Responsive CSS Grid / Flexbox) + Vanilla ES6+ JavaScript (zero heavy frontend frameworks)
- **Payment Gateway:** SSLCOMMERZ Hosted Payment Gateway V4 (REST API / Session Initiation + IPN / Validation Server)
- **PDF Generation & Printing:** ReportLab + CSS `@media print` optimized layout sheets
- **Static File Handling:** WhiteNoise with compressed manifest storage
- **WSGI Server:** Gunicorn

### `requirements.txt`
```text
Django>=5.0,<6.0
reportlab>=4.0.0
requests>=2.30.0
whitenoise>=6.6.0
dj-database-url>=2.1.0
psycopg2-binary>=2.9.9
gunicorn>=21.2.0
```

---

## 3. Project Directory Architecture

```text
tns_microfinance_project/
│
├── manage.py
├── requirements.txt
├── README.md
├── PROJECT_SPECIFICATION.md
│
├── tns_microfinance/            # Project Configuration
│   ├── __init__.py
│   ├── settings.py              # Environment, apps, middleware, SSLCOMMERZ settings
│   ├── urls.py                  # Master routing
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── accounts/                # User authentication, RBAC, profiles, officer staff
│   │   ├── migrations/
│   │   ├── decorators.py        # @admin_required, @officer_required, @member_required
│   │   ├── forms.py             # LoginForm, OfficerCreationForm, UserProfileForm
│   │   ├── models.py            # CustomUser (AbstractUser)
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── members/                 # Member KYC, profile management, nominee records
│   │   ├── migrations/
│   │   ├── forms.py             # MemberRegistrationForm, MemberProfileEditForm
│   │   ├── models.py            # MemberProfile
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── savings/                 # Savings accounts, deposit/withdrawal ledger, SSLCOMMERZ
│   │   ├── migrations/
│   │   ├── forms.py             # Deposit/Withdrawal request forms
│   │   ├── models.py            # SavingsAccount, SavingsTransaction, SSLPaymentSession
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── loans/                   # Loan products, applications, amortization schedules
│   │   ├── migrations/
│   │   ├── forms.py             # LoanApplicationForm, LoanSchemeForm
│   │   ├── models.py            # LoanScheme, LoanApplication, LoanInstallment, SSLLoanPaymentSession
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── core/                    # Dashboards, daily master reports, shared utilities
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── seed_data.py # Database seeder
│   │   ├── templatetags/
│   │   │   └── currency_tags.py # clean_amount, clean_bdt
│   │   ├── sslcommerz.py        # SSLCommerzGateway client wrapper
│   │   ├── utils.py             # Shared paginate, unique phone/email validators
│   │   ├── validators.py        # Bangladeshi phone & NID format validators
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── notifications/           # Notification dispatching and center
│       ├── migrations/
│       ├── models.py            # Notification
│       ├── utils.py             # notify_user, notify_staff_and_admins
│       ├── urls.py
│       └── views.py
│
├── static/
│   ├── css/
│   │   └── style.css            # Enterprise CSS Design System (CSS variables)
│   ├── js/
│   │   └── app.js               # Sidebar, Modals, Autocomplete, Input Masking, Loan Calc
│   └── images/
│
├── templates/
│   ├── base.html                # Master shell with responsive sidebar & topnav
│   ├── accounts/
│   ├── members/
│   ├── savings/
│   ├── loans/
│   ├── dashboard/
│   └── notifications/
│
└── media/                       # Profile pictures, KYC documents
```

---

## 4. Role-Based Access Control (RBAC) & Security

### 4.1 User Roles
1. **`ADMIN` (Superuser / Management):**
   - Full access to all modules, financial audits, daily master reports, staff account creation, loan scheme configuration, and system settings.
2. **`OFFICER` (Field / Branch Staff):**
   - Onboard members, review/approve member KYC, create loan applications on behalf of members, approve/disburse loans, verify manual deposits/withdrawals, collect loan installments in the field, and view daily collection sheets.
3. **`MEMBER` (Customer / Borrower):**
   - View their own personal dashboard, view savings account balance, request deposits/withdrawals, apply for loans, pay loan installments online (via Savings balance or SSLCOMMERZ), view running statements, and manage profile settings.

### 4.2 Security Decorators (`apps/accounts/decorators.py`)
- `@admin_required`: Validates `request.user.is_authenticated and (request.user.role == 'ADMIN' or request.user.is_superuser)`.
- `@officer_required`: Validates `request.user.is_authenticated and (request.user.role in ['OFFICER', 'ADMIN'] or request.user.is_superuser)`.
- `@member_required`: Validates `request.user.is_authenticated and request.user.role == 'MEMBER'`.
- Restrict cross-member access: When accessing a member profile, savings account, or loan record, verify `request.user.member_profile == target_member` if the user is a `MEMBER`.

---

## 5. Data Models & Database Schemas

### 5.1 Accounts App (`apps/accounts/models.py`)

#### `CustomUser` (Extends `AbstractUser`)
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `role` | CharField(20) | choices: `ADMIN`, `OFFICER`, `MEMBER`; default: `MEMBER` | Access tier |
| `phone` | CharField(15) | unique=True, null=True, blank=True | Validated BD mobile number |
| `profile_picture` | ImageField | upload_to='profile_pics/', blank=True, null=True | User portrait |
| `is_verified` | BooleanField | default=False | Identity verification flag |
| `date_joined` | DateTimeField | auto_now_add=True | Registration timestamp |

- **Helper Properties:** `is_admin_user`, `is_officer_user`, `is_member_user`.

---

### 5.2 Members App (`apps/members/models.py`)

#### `MemberProfile`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `user` | OneToOneField(`CustomUser`) | on_delete=CASCADE, related_name='member_profile' | Auth link |
| `member_id` | CharField(30) | unique=True | Format: `TNS-MEM-YYYY-XXXX` |
| `gender` | CharField(10) | choices: `MALE`, `FEMALE`, `OTHER` | Gender |
| `date_of_birth` | DateField | null=True, blank=True | DOB |
| `nid_number` | CharField(20) | unique=True | 10, 13, or 17 digits NID |
| `father_name` | CharField(100) | | Father's name |
| `mother_name` | CharField(100) | | Mother's name |
| `spouse_name` | CharField(100) | blank=True | Spouse name |
| `present_address` | TextField | | Current residence |
| `permanent_address`| TextField | | Legal permanent address |
| `occupation` | CharField(100) | | Profession/Trade |
| `monthly_income` | DecimalField | max_digits=12, decimal_places=2, default=0.00 | Monthly earnings |
| `nominee_name` | CharField(100) | | Beneficiary / Nominee |
| `nominee_relationship` | CharField(50) | | Relationship |
| `nominee_phone` | CharField(15) | | Nominee contact (must differ from member) |
| `nominee_nid` | CharField(20) | blank=True | Nominee NID (must differ from member) |
| `assigned_officer` | ForeignKey(`CustomUser`) | role='OFFICER', null=True, on_delete=SET_NULL | Managing field officer |
| `status` | CharField(20) | choices: `PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`; default: `PENDING` | Account status |
| `rejection_reason` | TextField | blank=True | Notes if rejected |
| `joined_date` | DateField | auto_now_add=True | Registration date |

- **Auto-Generation:** Generates `member_id` automatically in `save()` if blank using current year and sequential counter: `TNS-MEM-2026-0001`.

---

### 5.3 Savings App (`apps/savings/models.py`)

#### `SavingsAccount`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `member` | OneToOneField(`MemberProfile`) | on_delete=CASCADE, related_name='savings_account' | Account holder |
| `account_number` | CharField(30) | unique=True | Format: `SAV-XXXX` |
| `balance` | DecimalField | max_digits=14, decimal_places=2, default=0.00 | Current available balance |
| `created_at` | DateTimeField | auto_now_add=True | Opening timestamp |
| `updated_at` | DateTimeField | auto_now=True | Last activity timestamp |

#### `SavingsTransaction`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `account` | ForeignKey(`SavingsAccount`) | on_delete=CASCADE, related_name='transactions' | Savings ledger |
| `transaction_type`| CharField(20) | choices: `DEPOSIT`, `WITHDRAWAL` | Debit/Credit |
| `amount` | DecimalField | max_digits=12, decimal_places=2 | Monetary amount |
| `payment_method` | CharField(20) | choices: `CASH`, `BKASH`, `NAGAD`, `BANK`, `SSLCOMMERZ`, `SAVINGS` | Channel |
| `reference_note` | CharField(255) | blank=True | Trx note / Bank slip / MFS ID |
| `status` | CharField(20) | choices: `PENDING`, `APPROVED`, `REJECTED`; default: `PENDING` | Verification status |
| `created_by` | ForeignKey(`CustomUser`) | on_delete=SET_NULL, null=True | Initiator |
| `processed_by` | ForeignKey(`CustomUser`) | on_delete=SET_NULL, null=True, blank=True | Approving officer |
| `processed_at` | DateTimeField | null=True, blank=True | Approval timestamp |
| `created_at` | DateTimeField | auto_now_add=True | Transaction timestamp |

#### `SSLPaymentSession`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `tran_id` | CharField(100) | unique=True | Unique SSLCOMMERZ Trx ID |
| `val_id` | CharField(100) | blank=True, null=True | SSL validation ID |
| `account` | ForeignKey(`SavingsAccount`) | on_delete=CASCADE | Target savings account |
| `amount` | DecimalField | max_digits=12, decimal_places=2 | Deposit amount |
| `card_type` | CharField(100) | blank=True | Gateway payment method name |
| `bank_tran_id` | CharField(100) | blank=True | Gateway reference ID |
| `status` | CharField(20) | choices: `PENDING`, `VALID`, `FAILED`, `CANCELLED`; default: `PENDING` | Session status |
| `created_at` | DateTimeField | auto_now_add=True | Initiation timestamp |
| `validated_at` | DateTimeField | null=True, blank=True | Validation timestamp |

---

### 5.4 Loans App (`apps/loans/models.py`)

#### `LoanScheme`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `name` | CharField(100) | unique=True | E.g. "Micro Enterprise Loan" |
| `min_amount` | DecimalField | max_digits=12, decimal_places=2 | Minimum principal allowed |
| `max_amount` | DecimalField | max_digits=12, decimal_places=2 | Maximum principal allowed |
| `interest_rate_percent` | DecimalField | max_digits=5, decimal_places=2 | Annual flat interest percentage |
| `duration_months` | PositiveIntegerField | | Duration in months |
| `installment_frequency` | CharField(10) | choices: `MONTHLY`, `WEEKLY`; default: `MONTHLY` | Payment frequency |
| `penalty_rate_percent` | DecimalField | max_digits=5, decimal_places=2, default=0.00 | Overdue penalty rate |
| `description` | TextField | blank=True | Product brochure info |
| `is_active` | BooleanField | default=True | Active flag |

#### `LoanApplication`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `loan_id` | CharField(30) | unique=True | Format: `TNS-LN-YYYY-XXXX` |
| `member` | ForeignKey(`MemberProfile`) | on_delete=CASCADE, related_name='loans' | Borrower |
| `loan_product` | ForeignKey(`LoanScheme`) | null=True, on_delete=SET_NULL | Loan Scheme |
| `principal_amount` | DecimalField | max_digits=12, decimal_places=2 | Borrowed capital |
| `interest_rate` | DecimalField | max_digits=5, decimal_places=2 | Fixed rate |
| `duration_months` | PositiveIntegerField | | Loan period in months |
| `installment_frequency` | CharField(10) | choices: `MONTHLY`, `WEEKLY`; default: `MONTHLY` | Schedule frequency |
| `total_interest` | DecimalField | max_digits=12, decimal_places=2, default=0.00 | Calculated interest |
| `total_payable` | DecimalField | max_digits=12, decimal_places=2, default=0.00 | Principal + Interest |
| `total_paid` | DecimalField | max_digits=12, decimal_places=2, default=0.00 | Total repaid amount |
| `status` | CharField(20) | choices: `PENDING`, `APPROVED`, `REJECTED`, `DISBURSED`, `COMPLETED`; default: `PENDING` | Workflow stage |
| `purpose` | TextField | | Loan usage intent |
| `guarantor_name` | CharField(100) | | Guarantor full name |
| `guarantor_phone` | CharField(15) | | Guarantor mobile |
| `guarantor_nid` | CharField(20) | | Guarantor NID |
| `guarantor_relationship`| CharField(50) | | Guarantor relationship |
| `applied_at` | DateTimeField | auto_now_add=True | Application timestamp |
| `approved_by` | ForeignKey(`CustomUser`) | null=True, blank=True, on_delete=SET_NULL | Approving officer |
| `approved_at` | DateTimeField | null=True, blank=True | Approval timestamp |
| `disbursed_at` | DateTimeField | null=True, blank=True | Disbursement timestamp |

- **Model Properties:**
  - `remaining_balance`: `max(Decimal('0.00'), self.total_payable - self.total_paid)`
  - `total_installments`: `self.installments.count()`
  - `get_repayment_frequency_display()`: returns 'Weekly' or 'Monthly'

#### `LoanInstallment`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `loan` | ForeignKey(`LoanApplication`) | on_delete=CASCADE, related_name='installments' | Parent loan |
| `installment_number`| PositiveIntegerField | | Phase # (1, 2, 3...) |
| `due_date` | DateField | | Scheduled installment date |
| `principal_amount` | DecimalField | max_digits=12, decimal_places=2 | Principal component |
| `interest_amount` | DecimalField | max_digits=12, decimal_places=2 | Interest component |
| `total_amount` | DecimalField | max_digits=12, decimal_places=2 | Phase total due |
| `paid_amount` | DecimalField | max_digits=12, decimal_places=2, default=0.00 | Actual amount collected |
| `status` | CharField(20) | choices: `PENDING`, `PAID`, `OVERDUE`; default: `PENDING` | Phase status |
| `payment_method` | CharField(20) | choices: `CASH`, `SAVINGS`, `BKASH`, `NAGAD`, `BANK`, `SSLCOMMERZ`; blank=True | Repayment method |
| `payment_reference`| CharField(100) | blank=True | Trx reference |
| `paid_date` | DateField | null=True, blank=True | Actual payment date |
| `collected_by` | ForeignKey(`CustomUser`) | null=True, blank=True, on_delete=SET_NULL | Field officer / Staff |

- **Method `mark_as_paid(collector, payment_amount, method, reference)`**:
  - Updates `paid_amount`, `status = 'PAID'`, `payment_method`, `payment_reference`, `paid_date = timezone.now().date()`, `collected_by = collector`.
  - Increments `loan.total_paid += payment_amount`.
  - If `loan.total_paid >= loan.total_payable` or all installments are `PAID`, marks `loan.status = 'COMPLETED'`.

#### `SSLLoanPaymentSession`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `tran_id` | CharField(100) | unique=True | Unique Trx identifier |
| `val_id` | CharField(100) | blank=True, null=True | SSL validation ID |
| `installment` | ForeignKey(`LoanInstallment`) | on_delete=CASCADE | Target installment |
| `amount` | DecimalField | max_digits=12, decimal_places=2 | Repayment amount |
| `card_type` | CharField(100) | blank=True | Card/wallet used |
| `bank_tran_id` | CharField(100) | blank=True | Bank Trx ID |
| `status` | CharField(20) | choices: `PENDING`, `VALID`, `FAILED`, `CANCELLED`; default: `PENDING` | Session status |
| `created_at` | DateTimeField | auto_now_add=True | Created timestamp |
| `validated_at` | DateTimeField | null=True, blank=True | Validation timestamp |

---

### 5.5 Notifications App (`apps/notifications/models.py`)

#### `Notification`
| Field | Type | Attributes / Constraints | Description |
|---|---|---|---|
| `user` | ForeignKey(`CustomUser`) | on_delete=CASCADE, related_name='notifications' | Recipient |
| `title` | CharField(150) | | Alert heading |
| `message` | TextField | | Alert description |
| `link` | CharField(255) | blank=True | Redirect URL on click |
| `notification_type`| CharField(20) | choices: `INFO`, `SUCCESS`, `WARNING`, `DANGER`; default: `INFO` | Badge style |
| `is_read` | BooleanField | default=False | Read status |
| `created_at` | DateTimeField | auto_now_add=True | Dispatch timestamp |

---

## 6. Financial Calculations & Business Logic Rules

### 6.1 Flat Rate Loan Amortization Formula
Microfinance loans use the standard flat-rate calculation:
$$\text{Interest} = \text{Principal} \times \left(\frac{\text{Annual Rate}}{100}\right) \times \left(\frac{\text{Duration in Months}}{12}\right)$$
$$\text{Total Payable} = \text{Principal} + \text{Interest}$$

### 6.2 Installment Generation Logic (`loan.generate_installments()`)
- **Total Installments ($N$):**
  - If `installment_frequency == 'WEEKLY'`: $N = \text{duration\_months} \times 4$
  - If `installment_frequency == 'MONTHLY'`: $N = \text{duration\_months}$
- **Per-Installment Values:**
  - $\text{Principal Part} = \frac{\text{Principal}}{N}$
  - $\text{Interest Part} = \frac{\text{Interest}}{N}$
  - $\text{Installment Total} = \frac{\text{Total Payable}}{N}$
- **Due Date Scheduling:**
  - Disbursed on date $D$.
  - For phase $i \in [1, N]$:
    - Weekly: $\text{due\_date}_i = D + (i \times 7)\text{ days}$
    - Monthly: $\text{due\_date}_i = D + (i\text{ months})$ (handling month rollover cleanly via `relativedelta` or calendar calculations).

### 6.3 Repayment via Savings Deduction
When a member or officer selects "Deduction from savings" to pay an installment:
1. Ensure within `transaction.atomic()`.
2. Check `member.savings_account.balance >= installment.total_amount`. If not, abort and display an error.
3. Deduct amount from `savings_account.balance` and save.
4. Record an approved `SavingsTransaction` of type `WITHDRAWAL` with note: `Loan Phase #{i} Repayment ({loan_id})`.
5. Call `installment.mark_as_paid(collector=user, payment_amount=installment.total_amount, method='SAVINGS', reference=f"SAV-DEBIT-{account_number}")`.

### 6.4 Savings Running Balance Statement Generation
When calculating the statement for a date range $[D_{\text{start}}, D_{\text{end}}]$:
1. **Opening Balance:**
   $$\text{Opening Balance} = \sum \text{Deposits}_{(\text{date} < D_{\text{start}})} - \sum \text{Withdrawals}_{(\text{date} < D_{\text{start}})}$$
2. **Date Range Transactions:** Iterate chronologically from $D_{\text{start}}$ to $D_{\text{end}}$.
   - For each approved transaction:
     - If `DEPOSIT`: $\text{Running Balance} \mathrel{+}= \text{amount}$
     - If `WITHDRAWAL`: $\text{Running Balance} \mathrel{-}= \text{amount}$
3. **Closing Balance:**
   $$\text{Closing Balance} = \text{Opening Balance} + \text{Total Deposits}_{\text{range}} - \text{Total Withdrawals}_{\text{range}}$$

---

## 7. Input Validation & Data Integrity Standards

### 7.1 Bangladeshi Phone & NID Validators (`apps/core/validators.py`)
- **Phone Validator (`validate_bd_phone`):**
  - Strips all non-digit characters (`+88`, spaces, dashes).
  - Must start with Bangladeshi operator prefixes: `013`, `014`, `015`, `016`, `017`, `018`, or `019`.
  - Must be exactly 11 digits long.
- **NID Validator (`validate_nid_number`):**
  - Strips all non-digit characters.
  - Length must be exactly 10 (Smart Card), 13 (Old Format), or 17 digits (Full Format with Birth Year).
- **Nominee Conflict Check (`validate_nominee_mismatch`):**
  - Nominee's phone number cannot be identical to the applicant's phone number.
  - Nominee's NID number cannot be identical to the applicant's NID number.

### 7.2 Frontend Digit Masking (`static/js/app.js`)
- All inputs targeting phone or NID (`input[name*="phone"]`, `input[name*="nid"]`) enforce:
  - `inputmode="numeric"`, `pattern="[0-9]*"`.
  - `keydown` listener blocking non-digit keystrokes (allowing navigation keys: Arrow keys, Backspace, Tab, Enter, Delete).
  - `input` listener stripping any non-digit character via `.replace(/\D/g, '')`.
  - `paste` listener intercepting clipboard data and inserting only pure digits.

---

## 8. Payment Gateway Integration: SSLCOMMERZ V4

### 8.1 Gateway Settings (`tns_microfinance/settings.py`)
```python
SSLCOMMERZ_STORE_ID = os.environ.get('SSLCOMMERZ_STORE_ID', 'tnsco6a9fad1c04883')
SSLCOMMERZ_STORE_PASS = os.environ.get('SSLCOMMERZ_STORE_PASS', 'tnsco6a9fad1c04883@ssl')
SSLCOMMERZ_IS_SANDBOX = os.environ.get('SSLCOMMERZ_IS_SANDBOX', 'True') == 'True'
```

### 8.2 Client Service (`apps/core/sslcommerz.py`)
- **Endpoints:**
  - Sandbox Session: `https://sandbox.sslcommerz.com/gwprocess/v4/api.php`
  - Sandbox Validation: `https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php`
  - Live Session: `https://securepay.sslcommerz.com/gwprocess/v4/api.php`
  - Live Validation: `https://securepay.sslcommerz.com/validator/api/validationserverAPI.php`
- **Method `initiate_payment(...)`**:
  - Sends POST request with `store_id`, `store_passwd`, `total_amount`, `currency='BDT'`, `tran_id`, `success_url`, `fail_url`, `cancel_url`, and customer information.
  - Returns `GatewayPageURL` to redirect the user.
- **Method `validate_payment(...)`**:
  - Sends GET/POST request to the validation server API with `val_id`, `store_id`, `store_passwd`.
  - Confirms status is `VALID` or `VALIDATED`.

### 8.3 Handlers & Callbacks
- **Savings Online Deposit:**
  - Initiate: `savings:add_money_online`
  - Success callback (`@csrf_exempt`): `savings:sslcommerz_success` -> Validates `val_id`, updates `SSLPaymentSession.status = 'VALID'`, increments `SavingsAccount.balance`, records approved `SavingsTransaction(type='DEPOSIT', method='SSLCOMMERZ')`, dispatches success notifications to member and staff, and renders `savings/sslcommerz_receipt.html`.
  - Fail callback: `savings:sslcommerz_fail` -> Marks session `FAILED`, redirects to deposit form with warning.
  - Cancel callback: `savings:sslcommerz_cancel` -> Marks session `CANCELLED`, redirects with info message.
- **Loan Installment Repayment:**
  - Initiate: `loans:sslcommerz_initiate_installment`
  - Success callback (`@csrf_exempt`): `loans:sslcommerz_loan_success` -> Validates `val_id`, marks `SSLLoanPaymentSession.status = 'VALID'`, executes `installment.mark_as_paid(method='SSLCOMMERZ')`, dispatches notifications, and renders `loans/sslcommerz_loan_receipt.html`.
  - Fail / Cancel callbacks: marks session accordingly and redirects to `loans:loan_detail`.

---

## 9. Comprehensive URL & Routing Specification

### 9.1 Core Routing (`apps/core/urls.py` - namespace `core`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/` | `dashboard_dispatcher` | `@login_required` | Redirects to Admin, Officer, or Member dashboard |
| `/portal/member/` | `member_dashboard` | `@member_required` | Member dashboard (savings, active loans, next due) |
| `/portal/officer/` | `officer_dashboard` | `@officer_required` | Field officer dashboard (today's collections, dues) |
| `/portal/admin/` | `admin_dashboard` | `@admin_required` | Executive dashboard (capital disbursed, profit, cash) |
| `/portal/collection-sheet/` | `collection_sheet_view` | `@officer_required` | Daily field collection sheet by officer and date |
| `/portal/reports/` | `financial_reports_view` | `@admin_required` | Overall financial statement and cash movement |
| `/portal/daily-transactions/` | `daily_master_transactions_view` | `@admin_required` | Master daily inflow/outflow audit report |
| `/portal/daily-transactions/pdf/` | `daily_master_transactions_view` | `@admin_required` | PDF / Print version of daily report |

### 9.2 Accounts Routing (`apps/accounts/urls.py` - namespace `accounts`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/accounts/login/` | `login_view` | Public | Authentication login page |
| `/accounts/register/` | `register_view` | Public | Member self-registration |
| `/accounts/registration-submitted/` | `registration_submitted_view` | Public | Post-registration confirmation |
| `/accounts/logout/` | `logout_view` | Authenticated | Logout and session termination |
| `/accounts/profile/` | `profile_view` | Authenticated | User account and security profile |
| `/accounts/officers/` | `officer_list_view` | `@admin_required` | Staff accounts list & creation form |
| `/accounts/officers/<int:user_id>/toggle-status/` | `officer_toggle_status` | `@admin_required` | Activate / Deactivate staff user |

### 9.3 Members Routing (`apps/members/urls.py` - namespace `members`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/members/` | `member_list_view` | `@officer_required` | Searchable list of all members |
| `/members/create/` | `member_create_view` | `@officer_required` | Officer manual member KYC onboarding |
| `/members/<int:pk>/` | `member_detail_view` | Auth (Owner / Staff) | Full member KYC dossier, savings & loans |
| `/members/<int:pk>/edit/` | `member_edit_view` | `@officer_required` | Edit member profile |
| `/members/<int:pk>/approve/` | `member_approve_view` | `@officer_required` | Approve pending member account |
| `/members/<int:pk>/reject/` | `member_reject_view` | `@officer_required` | Reject pending member application |

### 9.4 Savings Routing (`apps/savings/urls.py` - namespace `savings`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/savings/my-account/` | `my_savings_view` | `@member_required` | Member's personal savings portal |
| `/savings/deposit-request/` | `member_deposit_request` | `@member_required` | Submit manual deposit request |
| `/savings/withdrawal-request/` | `member_withdrawal_request` | `@member_required` | Submit withdrawal request |
| `/savings/transactions/` | `staff_transaction_list` | `@officer_required` | Ledger transaction approval list |
| `/savings/record-deposit/` | `staff_record_deposit` | `@officer_required` | Officer counter/field deposit recording |
| `/savings/record-withdrawal/` | `staff_record_withdrawal`| `@officer_required` | Officer counter withdrawal recording |
| `/savings/transactions/<int:trx_id>/approve/` | `staff_approve_transaction` | `@officer_required` | Approve deposit/withdrawal |
| `/savings/transactions/<int:trx_id>/reject/` | `staff_reject_transaction` | `@officer_required` | Reject deposit/withdrawal |
| `/savings/statement/` | `savings_statement_view` | Authenticated | Member/Staff statement generator with dates |
| `/savings/statement/<int:member_id>/` | `savings_statement_view` | `@officer_required` | Direct member statement view |
| `/savings/add-money-online/` | `add_money_online_view` | `@member_required` | Initiate SSLCOMMERZ deposit |
| `/savings/sslcommerz/success/` | `sslcommerz_success_view` | Public (`@csrf_exempt`) | SSLCOMMERZ deposit callback |
| `/savings/sslcommerz/fail/` | `sslcommerz_fail_view` | Public (`@csrf_exempt`) | SSLCOMMERZ failure callback |
| `/savings/sslcommerz/cancel/` | `sslcommerz_cancel_view` | Public (`@csrf_exempt`) | SSLCOMMERZ cancellation callback |

### 9.5 Loans Routing (`apps/loans/urls.py` - namespace `loans`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/loans/my-loans/` | `my_loans_view` | `@member_required` | Member personal loan portfolio |
| `/loans/apply/` | `apply_loan_view` | `@member_required` | Member self-service loan application |
| `/loans/<int:pk>/` | `loan_detail_view` | Auth (Owner / Staff) | Loan details & installment schedule |
| `/loans/` | `staff_loan_list` | `@officer_required` | Staff loan applications & active portfolio |
| `/loans/create/` | `staff_create_loan` | `@officer_required` | Staff on-behalf loan origination |
| `/loans/<int:pk>/approve/` | `approve_loan` | `@officer_required` | Approve pending loan application |
| `/loans/<int:pk>/reject/` | `reject_loan` | `@officer_required` | Reject pending loan application |
| `/loans/<int:pk>/disburse/` | `disburse_loan` | `@officer_required` | Disburse capital & generate installments |
| `/loans/installments/<int:installment_id>/collect/` | `collect_installment` | `@officer_required` | Cash collection of an installment |
| `/loans/installments/<int:installment_id>/pay/` | `member_pay_installment`| Authenticated | Settle installment via savings deduction |
| `/loans/installments/<int:installment_id>/sslcommerz/`| `sslcommerz_initiate_installment` | Authenticated | Initiate online SSLCOMMERZ payment |
| `/loans/sslcommerz/success/` | `sslcommerz_loan_success_view` | Public (`@csrf_exempt`) | SSLCOMMERZ loan callback |
| `/loans/sslcommerz/fail/` | `sslcommerz_loan_fail_view` | Public (`@csrf_exempt`) | SSLCOMMERZ loan failure |
| `/loans/sslcommerz/cancel/` | `sslcommerz_loan_cancel_view` | Public (`@csrf_exempt`) | SSLCOMMERZ loan cancel |
| `/loans/schemes/` | `loan_schemes_list` | `@admin_required` | Configure loan schemes |
| `/loans/statement/` | `loan_statement_view` | Authenticated | General loan statement selector |
| `/loans/<int:pk>/statement/` | `loan_statement_view` | Authenticated | Amortization statement for specific loan |

### 9.6 Notifications Routing (`apps/notifications/urls.py` - namespace `notifications`)
| Path | View Function | Permission | Description |
|---|---|---|---|
| `/notifications/` | `notifications_list` | Authenticated | Notification inbox |
| `/notifications/<int:notification_id>/read/` | `mark_as_read` | Authenticated | Mark notification as read |
| `/notifications/mark-all-read/` | `mark_all_as_read` | Authenticated | Mark all notifications as read |

---

## 10. Frontend Architecture & Design System

### 10.1 Design Tokens (`static/css/style.css`)
```css
:root {
  --primary: #1e3a8a;          /* Deep navy */
  --primary-light: #3b82f6;    /* Vibrant blue */
  --primary-dark: #172554;
  --accent: #059669;           /* Emerald green */
  --accent-light: #10b981;
  --bg-main: #f8fafc;          /* Clean slate */
  --surface: #ffffff;
  --text-main: #0f172a;        /* High-contrast dark slate */
  --text-muted: #64748b;
  --border-color: #e2e8f0;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07);
}
```

### 10.2 Layout Components
- **Responsive Collapsible Sidebar:** Contains brand logo, user role badge, navigation links grouped logically (Dashboard, Members, Savings, Loans, Reports, Administration), and collapse button.
- **Top Navigation Bar:** Dynamic breadcrumbs / page title, real-time unread notification counter badge, user profile menu, and quick logout.
- **Metric Stat Cards (`.stats-grid`):** Displays label, large formatted number, and contextual subtitle.
- **Responsive Data Tables (`.table-responsive`):** Styled header, zebra-striping, status badges (`badge-success`, `badge-warning`, `badge-danger`), and actionable button groups.
- **Modals (`.modal-backdrop`, `.modal-content`):** Clean dialog boxes for payment confirmation and loan phase settlements.
- **Print Optimization (`@media print`):** Hides navigation, sidebars, filters, and action buttons; ensures statements and daily reports print as clean, professional letterhead documents.

### 10.3 Client-Side Logic (`static/js/app.js`)
1. **Sidebar Controller:** Handles opening, closing, backdrop click, and `Escape` key listeners.
2. **Modal Controller:** `window.openModal(id)` and `window.closeModal(id)` with outside-click dismissal.
3. **Dynamic Loan Calculator:** Automatically listens to changes on principal, duration, and scheme; calculates and renders estimated interest, total payable, and weekly/monthly installments.
4. **Member Search Autocomplete:** Real-time client-side filter against member lists, keyword highlighting (`<mark>`), and keyboard navigation (Arrow Up, Arrow Down, Enter, Escape).
5. **Strict Numeric-Only Restriction:** Restricts phone numbers and NIDs to pure digits (`[0-9]`) across typing, pasting, and mobile keypads.

---

## 11. Initial Data Seeder (`apps/core/management/commands/seed_data.py`)

A fully working system requires pre-populated roles and products. Executing `py manage.py seed_data` creates:

1. **System Administrator:**
   - Username: `admin` | Password: `admin123` | Role: `ADMIN`
2. **Field Officers:**
   - Username: `officer1` (Tareq Hasan) | Password: `123456` | Role: `OFFICER`
   - Username: `officer2` (Salma Khatun) | Password: `123456` | Role: `OFFICER`
3. **Standard Loan Schemes:**
   - **Micro Enterprise Loan:** Principal ৳10,000 – ৳200,000 | Rate: 10.00% | Duration: 12 Months | Monthly installments.
   - **Weekly Small Trade Loan:** Principal ৳5,000 – ৳50,000 | Rate: 8.00% | Duration: 6 Months | Weekly installments.
   - **Emergency Assistance Loan:** Principal ৳5,000 – ৳30,000 | Rate: 5.00% | Duration: 3 Months | Monthly installments.
4. **Pre-Enrolled Active Members:**
   - Rahim Uddin (`TNS-MEM-0001`, `SAV-0001`)
   - Fatema Begum (`TNS-MEM-0002`, `SAV-0002`)
   - Kamal Hossain (`TNS-MEM-0003`, `SAV-0003`)
   - Password for demo members: `123456`

---

## 12. Step-by-Step Implementation Execution Plan

When an AI agent is instructed to build this project from this specification, it should execute the build in the following ordered phases:

### Phase 1: Environment & Django Setup
1. Initialize virtual environment and install dependencies from `requirements.txt`.
2. Create Django project `tns_microfinance` and configure `settings.py`:
   - Add `apps` directory to `sys.path`.
   - Configure `INSTALLED_APPS`, `AUTH_USER_MODEL = 'accounts.CustomUser'`.
   - Setup static and media directories.
   - Configure SSLCOMMERZ environment variables.

### Phase 2: Core Utilities & Validators
1. Implement `apps/core/validators.py` with `validate_bd_phone` and `validate_nid_number`.
2. Implement `apps/core/utils.py` with `paginate`, `clean_phone_unique`, `clean_email_unique`, and `validate_nominee_mismatch`.
3. Implement `apps/core/templatetags/currency_tags.py` with `clean_amount` and `clean_bdt`.
4. Implement `apps/core/sslcommerz.py` with `SSLCommerzGateway`.

### Phase 3: Accounts & Role-Based Authentication
1. Implement `CustomUser` in `apps/accounts/models.py`.
2. Create RBAC decorators in `apps/accounts/decorators.py`.
3. Create login, registration, logout, profile, and officer management forms and views.
4. Build `templates/accounts/login.html`, `register.html`, `profile.html`, and `officer_list.html`.

### Phase 4: Member Management & KYC
1. Implement `MemberProfile` in `apps/members/models.py` with auto-generating `member_id`.
2. Create `MemberValidationMixin`, `MemberRegistrationForm`, and `MemberProfileEditForm`.
3. Create views for member listing, KYC onboarding, detail dossiers, and approval/rejection workflows.
4. Build `templates/members/member_list.html`, `member_create.html`, `member_detail.html`, and `member_edit.html`.

### Phase 5: Savings Ledger & Statement Generator
1. Implement `SavingsAccount`, `SavingsTransaction`, and `SSLPaymentSession` in `apps/savings/models.py`.
2. Create deposit/withdrawal forms with built-in boundary validation.
3. Build member savings portal (`my_savings.html`), staff transaction verification queue (`staff_transactions.html`), and running balance statement generator (`savings_statement.html`).
4. Implement SSLCOMMERZ online deposit flow (`add_money_online.html`, receipt, callbacks).

### Phase 6: Loan Origination, Amortization Engine & Payments
1. Implement `LoanScheme`, `LoanApplication`, `LoanInstallment`, and `SSLLoanPaymentSession` in `apps/loans/models.py`.
2. Implement the amortization installment generation algorithm in `LoanApplication.generate_installments()`.
3. Build member loan application portal (`apply_loan.html`), staff loan queue (`staff_loan_list.html`, `staff_create_loan.html`), and loan detail schedule view (`loan_detail.html`).
4. Implement dual repayment methods:
   - Settle phase via savings deduction with atomic transaction balance check.
   - Settle phase via SSLCOMMERZ online payment gateway.
5. Build loan amortization statement view (`loan_statement.html`).

### Phase 7: Executive Dashboards, Reports & Notifications
1. Implement `Notification` model and utilities in `apps/notifications/`.
2. Implement dashboard dispatcher and three role-specific dashboards:
   - `admin_dashboard.html`: Aggregated capital, profit, and pending queues.
   - `officer_dashboard.html`: Today's collections, dues, and field queues.
   - `member_dashboard.html`: Savings summary, active loans, and upcoming installment.
3. Implement `collection_sheet.html`, `financial_reports.html`, and `daily_master_report.html` with print styling.

### Phase 8: Frontend Polish & Client-Side Scripts
1. Build `static/css/style.css` using the enterprise CSS variables design system.
2. Build `static/js/app.js` with modal controller, sidebar controller, loan calculator, member search autocomplete, and phone/NID numeric input masking.

### Phase 9: Seeding & Verification
1. Create `apps/core/management/commands/seed_data.py`.
2. Run database migrations: `py manage.py makemigrations && py manage.py migrate`.
3. Execute `py manage.py seed_data`.
4. Execute `py manage.py check` and automated unit tests `py manage.py test` to ensure 100% compliance.

---

## 13. System Verification & Acceptance Criteria

A compliant installation of this system must pass the following checks:
1. **Zero System Errors:** `py manage.py check` returns `0 issues`.
2. **Automated Test Suite:** `py manage.py test` runs with all test cases passing.
3. **RBAC Isolation:** A member attempting to access `/portal/admin/` or `/members/` is redirected or blocked.
4. **Data Masking:** Non-numeric characters cannot be typed or pasted into phone or NID fields.
5. **Loan Math Accuracy:**
   - Borrowing ৳10,000 at 10% for 12 months produces exactly ৳1,000 interest, ৳11,000 total payable, and 12 monthly installments of ৳916.67.
   - Paying an installment marks it as `PAID`, adds to `total_paid`, and reduces `remaining_balance`.
6. **Savings Integrity:** An attempt to withdraw or pay a loan installment exceeding the available savings balance is rejected with an atomic rollback.
7. **Payment Gateway:** Initiating an SSLCOMMERZ transaction redirects to the official sandbox gateway URL with valid session parameters, and sandbox payment callbacks correctly settle the corresponding ledger.

---
*(End of Master System Specification)*
