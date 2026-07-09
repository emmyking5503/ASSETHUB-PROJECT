import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multi_market.settings')
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=2)
