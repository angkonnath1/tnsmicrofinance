# 🏦 Touch & Solve - Microfinance Co-operative System

> **A Full-Stack Django Capstone & Learning Project**  
> *Developed by a Beginner Learner Developer using Python, Django 5, and Vanilla CSS.*

---

## 🌟 About This Project

Welcome to the **Touch & Solve Microfinance Co-operative System**! 

I built this project to learn and demonstrate how modern financial applications and cooperative societies operate in the real world. In Bangladesh and throughout South Asia, microfinance organizations empower communities by offering simple savings accounts, micro-loans, and daily field collections.

This application is designed from the ground up to be **clean, robust, easy to read, and fully functional**, following standard Django best practices taught in beginner Python web development courses.

---

## 🎓 What I Learned While Building This Project

Building this application helped me master fundamental and intermediate Django concepts:

1. **Django MVT Pattern (Model - View - Template)**:
   - Kept business logic clean by separating database models (`models.py`), request handlers (`views.py`), and presentation templates (`templates/`).
2. **Role-Based Access Control (RBAC)**:
   - Created a `CustomUser` model inheriting from `AbstractUser` with three user roles: **Admin**, **Field Officer**, and **Member**.
   - Wrote custom view decorators (`@admin_required`, `@officer_required`, `@member_required`) to protect sensitive routes.
3. **Relational Database Design & Django ORM**:
   - Designed one-to-one relationships (User &rarr; MemberProfile, MemberProfile &rarr; SavingsAccount).
   - Designed one-to-many relationships (Member &rarr; Loans, Loan &rarr; Installments, Account &rarr; Transactions).
   - Used Django ORM aggregations (`aggregate(Sum('amount'))`) to compute financial totals cleanly.
4. **Data Integrity & Atomic Transactions**:
   - Used `django.db.transaction.atomic` for multi-step financial actions (e.g. approving a deposit credits the balance and records the transaction together safely).
5. **Django Forms & File Uploads**:
   - Used `forms.ModelForm` with clean CSRF protection and handled member KYC photo uploads.
6. **In-App Notifications**:
   - Built a trigger-based notification engine with a custom context processor so unread alerts appear instantly in the top navigation bar.
7. **Printable Statements**:
   - Created clean, responsive HTML statement templates with standard browser printing (`window.print()`).

---

## 👥 The 3 Core Roles & Features

### 1. 👤 Cooperative Member
- **Dashboard**: Live overview of savings balance, active loan balances, and next upcoming installment due date.
- **My Savings**: View deposit and withdrawal history. Submit manual deposit requests (Cash, bKash, or Nagad with TrxID) for officer verification, or request withdrawals.
- **My Loans**: View ongoing loans with visual progress bars. Apply for loans from active schemes. View complete monthly installment breakdown and pay installments directly from savings balance or cash.
- **My Profile**: Read-only KYC record displaying verified personal info, NID number, and nominee details.

### 2. 👔 Field Officer
- **Dashboard**: Operational queue showing today's field collections, pending member signups, pending deposit requests, and pending loan applications.
- **Member Management**: Enroll new members with automated Member IDs (`TNS-MEM-xxxx`), upload KYC photos, and review documents.
- **Savings Verification**: Review member deposit and withdrawal requests with one-click **Approve** or **Reject** actions.
- **Loan Management**: Review loan applications, approve loans, and **Disburse** loans (which automatically generates the monthly installment schedule).
- **Daily Collection Sheet**: Fast, printable field sheet for recording savings and installment recoveries during field visits.

### 3. 👑 System Admin (Cooperative Owner)
- **Executive Portal**: Real-time financial dashboard displaying:
  - Total Savings Liquidity
  - Total Capital Disbursed
  - Total Repayments Collected
  - Total Outstanding Credit & Net Earnings
- **Staff Management**: Create and oversee Field Officers.
- **Loan Products**: Configure loan schemes with customized interest rates, minimum/maximum amounts, and repayment durations.
- **Daily Master Daybook & Reports**: Comprehensive daily cash inflow vs outflow ledger with browser print / save-to-PDF support.

---

## 📂 Project Architecture

```text
Co Op TNS/
│
├── apps/
│   ├── accounts/          # Custom user model, login/logout, profile views, officer management
│   ├── members/           # Member KYC profiles, photo uploads, nominee records
│   ├── savings/           # Savings accounts, deposit/withdrawal requests, officer approvals
│   ├── loans/             # Loan products, applications, monthly installment schedules, repayments
│   ├── core/              # Role-based dashboard dispatcher, collection sheet, master daybook
│   └── notifications/     # In-app notifications engine and topbar context processor
│
├── templates/             # HTML5 templates styled with modern Vanilla CSS
│   ├── accounts/          # Login, registration, profile templates
│   ├── dashboard/         # Admin, Officer, Member dashboards, collection sheet, daybook
│   ├── loans/             # Loan detail, apply form, schemes, statement
│   └── savings/           # My savings, transactions list, statement
│
├── static/                # Vanilla CSS (style.css) and responsive sidebar JavaScript (app.js)
├── tns_microfinance/      # Project settings, WSGI, and root URL routing
├── seed_data.py           # Pre-seeds the database with test members, loans, and transactions
├── manage.py              # Django management CLI
└── README.md              # Project documentation
```

---

## 🚀 Quick Setup Guide

You can run this project locally in less than 2 minutes:

### 1. Run Database Migrations
```bash
python manage.py migrate
```

### 2. Seed Sample Demo Data
```bash
python seed_data.py
```
*(This automatically creates the admin account, two field officers, and three active members with pre-populated savings and loans!)*

### 3. Start the Development Server
```bash
python manage.py runserver
```

Open your browser and visit: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🔑 Pre-Configured Test Accounts

| Role | Username | Password | Direct Dashboard Link |
| :--- | :--- | :--- | :--- |
| **👑 Admin (Owner)** | `admin` | `admin123` | `/portal/admin/` |
| **👔 Field Officer 1** | `officer1` | `123456` | `/portal/officer/` |
| **👔 Field Officer 2** | `officer2` | `123456` | `/portal/officer/` |
| **👤 Member (Rahim)** | `rahim` | `123456` | `/portal/member/` |
| **👤 Member (Fatema)** | `fatema` | `123456` | `/portal/member/` |
| **👤 Member (Kamal)** | `kamal` | `123456` | `/portal/member/` |

---

## 🎬 Step-by-Step Project Walkthrough / Demo Script

Use this sequence to demonstrate the application to teachers, interviewers, or classmates:

### Step 1: Member Experience (`rahim` / `123456`)
1. Log in as member **`rahim`**.
2. **Dashboard**: Notice the clear financial cards: Savings Balance, Active Loans, and Next Installment Due.
3. **Savings Deposit**: Go to **My Savings** &rarr; click **Deposit Money** &rarr; submit a deposit of `1,000 BDT` via `bKash` with a TrxID (e.g. `TRX98765`). Notice the status is set to **Pending Approval**.
4. **Loan Details**: Go to **My Loans** &rarr; click on active loan `TNS-LN-0001`. Notice the installment schedule with due dates, paid statuses, and remaining balance.
5. **Member Profile**: Click **Profile** in the sidebar. Notice the verified KYC details (NID, photo, nominee information) presented in a secure, read-only format.

### Step 2: Officer Experience (`officer1` / `123456`)
1. Log out and log in as field officer **`officer1`**.
2. **Approve Deposit**: Go to **Savings** &rarr; **Transactions** &rarr; find Rahim's pending `1,000 BDT` deposit &rarr; click **Approve**. 
   *(Django automatically credits Rahim's savings account balance and sends an in-app notification!)*
3. **Members**: Go to **Members** to view the member directory and search by name or member ID.
4. **Collection Sheet**: Go to **Collection Sheet** &rarr; choose today's date &rarr; click **Print / Save as PDF** to see the print-ready collection report.

### Step 3: Admin Experience (`admin` / `admin123`)
1. Log out and log in as **`admin`**.
2. **Executive Financials**: Inspect the real-time cashflow metrics: Total Liquidity, Capital Disbursed, Repayments Collected, and Operational Profit.
3. **Staff Management**: Go to **Staff Officers** to view or create field officer accounts.
4. **Loan Products**: Go to **Loan Products** to see how standard credit schemes (rates, durations) are configured.
5. **Daybook Report**: Go to **Daybook** &rarr; click **Print / Save as PDF** to view the institution-wide audit trail for the day.

---

## 🧪 Running Automated Tests

To run the automated test suite:
```bash
python manage.py test
```

To run Django's internal system check:
```bash
python manage.py check
```

---

## 💡 Technologies Used
- **Backend**: Python 3, Django 5
- **Database**: SQLite3 (Standard, zero-config)
- **Frontend**: HTML5, Vanilla CSS (Custom Plus Jakarta Sans design system), Vanilla JavaScript
- **Print Engine**: CSS `@media print` with browser-native `window.print()`
