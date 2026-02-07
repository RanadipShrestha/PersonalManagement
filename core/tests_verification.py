from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date
from .models import Todo, Journal, Transaction, LifeGoal, BuyShare, SellShare

class VerificationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')

    # ... Previous tests ...

    def test_share_pnl_calculation(self):
        self.client.login(username='user1', password='password123')
        
        # Buy 100 shares @ 10
        buy_share = BuyShare.objects.create(
            user=self.user1, company_name='PnLCorp', price_per_share=10, quantity=100, total_price=1000, target_holding_period='1Y'
        )
        
        # Sell 50 shares @ 15 (Profit = 5 * 50 = 250)
        SellShare.objects.create(
            user=self.user1, buy_share=buy_share, sell_price_per_share=15, quantity_sold=50, sell_date=timezone.now().date()
        )
        
        response = self.client.get(reverse('share-dashboard'))
        self.assertEqual(response.context['total_realized_pnl'], 250.0)
        self.assertEqual(response.context['total_sales_value'], 750.0) # 50 * 15
        self.assertEqual(response.context['total_current_investment'], 500.0) # 50 remaining * 10
        
        # Check if 'PnLCorp' is in current_holdings
        self.assertEqual(len(response.context['current_holdings']), 1)
        self.assertEqual(response.context['current_holdings'][0].company_name, 'PnLCorp')
        
        # Sell remaining 50 @ 5 (Loss = -5 * 50 = -250)
        # Net P/L should be 0
        SellShare.objects.create(
            user=self.user1, buy_share=buy_share, sell_price_per_share=5, quantity_sold=50, sell_date=timezone.now().date()
        )
        
        response = self.client.get(reverse('share-dashboard'))
        self.assertEqual(response.context['total_realized_pnl'], 0.0)
        self.assertEqual(response.context['total_current_investment'], 0.0)
        
        # Check if 'PnLCorp' is REMOVED from current_holdings
        self.assertEqual(len(response.context['current_holdings']), 0)
        # But still in buy_history
        self.assertEqual(len(response.context['buy_history']), 1)
