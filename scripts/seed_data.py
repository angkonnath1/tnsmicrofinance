import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tns_microfinance.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    call_command('seed_data')
