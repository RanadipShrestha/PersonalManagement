from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import MonthlyParticipation, ParticipationClick
from decimal import Decimal
import datetime

class MonthlyParticipationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

    def test_initial_creation(self):
        # Accessing the view should create the participation object
        from django.urls import reverse
        response = self.client.get(reverse('participation-detail'))
        self.assertEqual(response.status_code, 200)
        
        participation = MonthlyParticipation.objects.get(user=self.user)
        self.assertEqual(participation.current_amount, Decimal('1000.00'))
        
    def test_growth_logic_50_percent(self):
        # Set last_processed_date to 1 month ago
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        # Handle year wrap around if today is Jan
        if current_month_start.month == 1:
            last_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            last_month_start = current_month_start.replace(month=current_month_start.month - 1)
            
        participation = MonthlyParticipation.objects.create(
            user=self.user,
            current_amount=Decimal('1000.00'),
            last_processed_date=last_month_start
        )
        
        # Accessing the view should trigger growth for the missing month (last_month)
        from django.urls import reverse
        response = self.client.get(reverse('participation-detail'))
        
        participation.refresh_from_db()
        # No payment made for last_month, so 50% growth
        self.assertEqual(participation.current_amount, Decimal('1500.00'))
        self.assertEqual(participation.last_processed_date, current_month_start)

    def test_growth_logic_2_5_percent(self):
        # Set last_processed_date to 1 month ago
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        if current_month_start.month == 1:
            last_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            last_month_start = current_month_start.replace(month=current_month_start.month - 1)
            
        participation = MonthlyParticipation.objects.create(
            user=self.user,
            current_amount=Decimal('1000.00'),
            last_processed_date=last_month_start
        )
        
        # Record payment for last_month
        ParticipationClick.objects.create(
            user=self.user,
            click_date=last_month_start + datetime.timedelta(days=10)
        )
        
        from django.urls import reverse
        self.client.get(reverse('participation-detail'))
        
        participation.refresh_from_db()
        # 2.5% growth
        self.assertEqual(participation.current_amount, Decimal('1025.00'))

    def test_record_click_multiple_times(self):
        from django.urls import reverse
        # Initialize participation
        self.client.get(reverse('participation-detail'))
        
        # Click once
        self.client.post(reverse('record-participation-click'))
        self.assertEqual(ParticipationClick.objects.filter(user=self.user).count(), 1)
        
        # Click again in same month
        self.client.post(reverse('record-participation-click'))
        self.assertEqual(ParticipationClick.objects.filter(user=self.user).count(), 1)
