from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Member
    path('my-loans/', views.my_loans_view, name='my_loans'),
    path('apply/', views.apply_loan_view, name='apply_loan'),

    # Shared
    path('<int:pk>/', views.loan_detail_view, name='loan_detail'),

    # Staff / Admin
    path('', views.staff_loan_list, name='staff_loan_list'),
    path('create/', views.staff_create_loan, name='staff_create_loan'),
    path('<int:pk>/approve/', views.approve_loan, name='approve_loan'),
    path('<int:pk>/reject/', views.reject_loan, name='reject_loan'),
    path('<int:pk>/disburse/', views.disburse_loan, name='disburse_loan'),
    path('installments/<int:installment_id>/collect/', views.collect_installment, name='collect_installment'),
    path('installments/<int:installment_id>/pay/', views.member_pay_installment, name='pay_installment'),

    # SSLCOMMERZ Loan Installment Gateway
    path('installments/<int:installment_id>/sslcommerz/', views.sslcommerz_initiate_installment, name='sslcommerz_initiate_installment'),
    path('sslcommerz/success/', views.sslcommerz_loan_success_view, name='sslcommerz_loan_success'),
    path('sslcommerz/fail/', views.sslcommerz_loan_fail_view, name='sslcommerz_loan_fail'),
    path('sslcommerz/cancel/', views.sslcommerz_loan_cancel_view, name='sslcommerz_loan_cancel'),

    # Schemes
    path('schemes/', views.loan_schemes_list, name='schemes_list'),

    # Statement Generator
    path('statement/', views.loan_statement_view, name='general_statement'),
    path('<int:pk>/statement/', views.loan_statement_view, name='loan_statement'),
]

