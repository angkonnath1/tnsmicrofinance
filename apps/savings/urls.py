from django.urls import path
from . import views

app_name = 'savings'

urlpatterns = [
    # Member routes
    path('my-account/', views.my_savings_view, name='my_savings'),
    path('deposit-request/', views.member_deposit_request, name='deposit_request'),
    path('withdrawal-request/', views.member_withdrawal_request, name='withdrawal_request'),

    # Staff / Admin routes
    path('transactions/', views.staff_transaction_list, name='staff_transactions'),
    path('record-deposit/', views.staff_record_deposit, name='record_deposit'),
    path('record-withdrawal/', views.staff_record_withdrawal, name='record_withdrawal'),
    path('transactions/<int:trx_id>/approve/', views.staff_approve_transaction, name='approve_transaction'),
    path('transactions/<int:trx_id>/reject/', views.staff_reject_transaction, name='reject_transaction'),
    path('statement/', views.savings_statement_view, name='statement'),
    path('statement/<int:member_id>/', views.savings_statement_view, name='member_statement'),

    # SSLCOMMERZ Official Sandbox Hosted Payment Gateway
    path('add-money-online/', views.add_money_online_view, name='add_money_online'),
    path('sslcommerz/success/', views.sslcommerz_success_view, name='sslcommerz_success'),
    path('sslcommerz/fail/', views.sslcommerz_fail_view, name='sslcommerz_fail'),
    path('sslcommerz/cancel/', views.sslcommerz_cancel_view, name='sslcommerz_cancel'),
]

