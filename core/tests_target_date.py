from django.test import TestCase
from django.contrib.auth.models import User
import datetime
from core.models import BuyShare

class TargetDateCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_auto_calculate_year(self):
        buy = BuyShare.objects.create(
            user=self.user,
            company_name='TestCorp',
            price_per_share=10,
            quantity=100,
            total_price=1000,
            buy_date=datetime.date(2026, 1, 1),
            target_holding_period='1 year'
        )
        self.assertEqual(buy.target_date, datetime.date(2027, 1, 1))

    def test_auto_calculate_month(self):
        buy = BuyShare.objects.create(
            user=self.user,
            company_name='TestCorp',
            price_per_share=10,
            quantity=100,
            total_price=1000,
            buy_date=datetime.date(2026, 1, 31),
            target_holding_period='1 month'
        )
        # Should be Feb 28
        self.assertEqual(buy.target_date, datetime.date(2026, 2, 28))

    def test_auto_calculate_days(self):
        buy = BuyShare.objects.create(
            user=self.user,
            company_name='TestCorp',
            price_per_share=10,
            quantity=100,
            total_price=1000,
            buy_date=datetime.date(2026, 1, 1),
            target_holding_period='30 days'
        )
        self.assertEqual(buy.target_date, datetime.date(2026, 1, 31))

    def test_manual_date_preserved(self):
        manual_date = datetime.date(2030, 1, 1)
        buy = BuyShare.objects.create(
            user=self.user,
            company_name='TestCorp',
            price_per_share=10,
            quantity=100,
            total_price=1000,
            buy_date=datetime.date(2026, 1, 1),
            target_holding_period='1 year',
            target_date=manual_date
        )
        self.assertEqual(buy.target_date, manual_date)
