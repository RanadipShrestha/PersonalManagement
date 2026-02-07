import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "journey.settings")
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import BuyShare
from django.utils import timezone

try:
    user = User.objects.get(username='debug_user')
    user.set_password('password')
    user.save()
except User.DoesNotExist:
    user = User.objects.create_user('debug_user', 'email@example.com', 'password')

client = Client()
client.login(username='debug_user', password='password')

buy = BuyShare.objects.create(user=user, company_name='DebugCorp', price_per_share=10, quantity=100, total_price=1000, target_holding_period='1Y')

print("Testing Missing Fields...")
response = client.post(reverse('sellshare-create'), {
    'buy_share': buy.pk,
    'quantity_sold': 10,
    'sell_date': timezone.now().date(),
    'notes': 'Debug Note'
})

print("Status:", response.status_code)
if response.context and 'form' in response.context:
    print("Errors:", response.context['form'].errors)
else:
    print("No form in context")

print("-" * 20)

print("Testing Calculation...")
response = client.post(reverse('sellshare-create'), {
    'buy_share': buy.pk,
    'quantity_sold': 10,
    'total_sale_amount': 200,
    'sell_date': timezone.now().date(),
    'notes': 'Debug Calc'
})
print("Status:", response.status_code)
if response.status_code == 302:
    print("Redirects to:", response.url)
else:
    if response.context and 'form' in response.context:
        print("Errors:", response.context['form'].errors)

# Cleanup
buy.delete()
user.delete()
