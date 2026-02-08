from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import BuyShare, SellShare

class SellShareCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.buy_share = BuyShare.objects.create(
            user=self.user, 
            company_name='TestCorp', 
            price_per_share=10, 
            quantity=100, 
            total_price=1000, 
            target_holding_period='1Y'
        )
        self.client.login(username='testuser', password='password')

    def test_calculate_price_from_total_amount(self):
        # Sell 10 shares for Total Amount 200 (Implies Price = 20)
        data = {
            'buy_share': self.buy_share.pk,
            'quantity_sold': 10,
            'total_sale_amount': 200,
            # 'sell_price_per_share': '', # Intentionally empty
            'sell_date': timezone.now().date(),
            'notes': 'Test Sale'
        }
        response = self.client.post(reverse('sellshare-create'), data)
        self.assertEqual(response.status_code, 302) # Redirects on success
        
        # Check created object
        sale = SellShare.objects.first()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.quantity_sold, 10)
        self.assertEqual(sale.sell_price_per_share, 20.00)

    def test_validation_error_missing_both(self):
        # Missing both price and total amount
        data = {
            'buy_share': self.buy_share.pk,
            'quantity_sold': 10,
            'sell_date': timezone.now().date(),
        }
        response = self.client.post(reverse('sellshare-create'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide either Sell Price per Share OR Total Sale Amount.", status_code=200)

    def test_double_entry_preference(self):
        # Update: If both are provided, let's say we trust the Price Per Share? 
        # Or recalculate? My logic says "If not sell_price_per_share...". 
        # So if sell_price IS provided, it uses it.
        data = {
            'buy_share': self.buy_share.pk,
            'quantity_sold': 10,
            'sell_price_per_share': 15,
            'total_sale_amount': 500, # This would imply 50/share, but we provided 15 explicitly
            'sell_date': timezone.now().date(),
        }
        response = self.client.post(reverse('sellshare-create'), data)
        self.assertEqual(response.status_code, 302)
        sale = SellShare.objects.first()
        self.assertEqual(sale.sell_price_per_share, 15.00)
