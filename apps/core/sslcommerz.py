import logging
import requests
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)

class SSLCommerzGateway:
    """
    Official SSLCOMMERZ V4 Hosted Payment Gateway Integration Service (Sandbox & Live).
    Interacts directly with official SSLCOMMERZ Session & Validation Server APIs.
    """
    def __init__(self):
        self.store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'tnsco6a9fad1c04883')
        self.store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', 'tnsco6a9fad1c04883@ssl')
        self.is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)

        if self.is_sandbox:
            self.session_api = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            self.validation_api = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
        else:
            self.session_api = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
            self.validation_api = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"

    def initiate_payment(self, tran_id, amount, customer, success_url, fail_url, cancel_url, ipn_url=None, product_name="Co-op Financial Service"):
        """
        Calls official SSLCOMMERZ Session API to create a gateway session and get the GatewayPageURL.
        """
        phone = getattr(customer, 'phone', '') or '01711223344'
        email = getattr(customer, 'email', '') or 'member@touchandsolve.org'
        name = customer.get_full_name() if hasattr(customer, 'get_full_name') else str(customer)

        post_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_pass,
            'total_amount': f"{Decimal(str(amount)):.2f}",
            'currency': 'BDT',
            'tran_id': str(tran_id),
            'success_url': success_url,
            'fail_url': fail_url,
            'cancel_url': cancel_url,
            'ipn_url': ipn_url or success_url,
            
            # Customer Profile Info
            'cus_name': name or 'Touch & Solve Member',
            'cus_email': email or 'member@touchandsolve.org',
            'cus_add1': 'House 12, Road 4, Dhanmondi',
            'cus_city': 'Dhaka',
            'cus_state': 'Dhaka',
            'cus_postcode': '1205',
            'cus_country': 'Bangladesh',
            'cus_phone': phone or '01711223344',
            
            # Product Details
            'product_name': product_name,
            'product_category': 'Microfinance / Financial Service',
            'product_profile': 'general',
            'shipping_method': 'NO',
            'num_of_item': 1,
        }

        try:
            logger.info(f"Initiating SSLCOMMERZ Sandbox Session for tran_id: {tran_id}, amount: {amount}")
            response = requests.post(self.session_api, data=post_data, timeout=15)
            res_json = response.json()
            
            if res_json.get('status') == 'SUCCESS' and res_json.get('GatewayPageURL'):
                return {
                    'status': 'SUCCESS',
                    'gateway_url': res_json.get('GatewayPageURL'),
                    'sessionkey': res_json.get('sessionkey'),
                    'raw': res_json
                }
            else:
                logger.error(f"SSLCOMMERZ session creation failed: {res_json}")
                return {
                    'status': 'FAILED',
                    'message': res_json.get('failedreason', 'Unable to initiate SSLCOMMERZ gateway session'),
                    'raw': res_json
                }
        except Exception as e:
            logger.exception(f"SSLCOMMERZ API request exception: {e}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }

    def validate_payment(self, val_id, tran_id=None):
        """
        Calls official SSLCOMMERZ Validation Server API to verify that a transaction was genuinely paid.
        """
        if not val_id:
            return {'status': 'FAILED', 'message': 'Missing validation ID (val_id)'}

        params = {
            'val_id': val_id,
            'store_id': self.store_id,
            'store_passwd': self.store_pass,
            'format': 'json'
        }

        try:
            logger.info(f"Validating SSLCOMMERZ Transaction val_id: {val_id}")
            response = requests.get(self.validation_api, params=params, timeout=15)
            data = response.json()
            
            status = data.get('status')
            if status in ['VALID', 'VALIDATED']:
                return {
                    'status': 'VALID',
                    'val_id': data.get('val_id'),
                    'tran_id': data.get('tran_id') or tran_id,
                    'amount': data.get('amount'),
                    'currency': data.get('currency', 'BDT'),
                    'card_type': data.get('card_type', 'SSLCOMMERZ-Online'),
                    'card_no': data.get('card_no', ''),
                    'bank_tran_id': data.get('bank_tran_id', ''),
                    'raw': data
                }
            else:
                return {
                    'status': status or 'FAILED',
                    'message': data.get('error', 'Transaction validation failed'),
                    'raw': data
                }
        except Exception as e:
            logger.exception(f"SSLCOMMERZ Validation API error: {e}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }

sslcommerz_client = SSLCommerzGateway()
