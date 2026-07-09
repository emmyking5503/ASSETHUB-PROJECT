import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'multi_market.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()
user, created = User.objects.get_or_create(
    username='admincheck',
    defaults={'email':'admincheck@example.com', 'is_superuser': True, 'is_staff': True, 'is_active': True}
)
if created:
    user.set_password('admincheck123')
    user.save()

client = Client()
client.force_login(user)
urls = [
    reverse('super_admin'),
    reverse('admin_listings'),
    reverse('admin_transactions'),
    reverse('admin_reports'),
    reverse('admin_disputes'),
    reverse('notifications'),
    reverse('add_category'),
]
for url in urls:
    response = client.get(url)
    print(url, response.status_code)
