from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Journal(models.Model):
    MOOD_CHOICES = [
        ('Happy', 'Happy'),
        ('Sad', 'Sad'),
        ('Neutral', 'Neutral'),
        ('Excited', 'Excited'),
        ('Angry', 'Angry'),
        ('Anxious', 'Anxious'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    title = models.CharField(max_length=200)
    content = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True, null=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('Need', 'Need'),
        ('Want', 'Want'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    is_expense = models.BooleanField(default=True) # True for Expense, False for Income
    expense_type = models.CharField(max_length=10, choices=TYPE_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.amount} - {self.notes[:20]}"

class LifeGoal(models.Model):
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('Started', 'Started'),
        ('In Progress', 'In Progress'),
        ('50% Completed', '50% Completed'),
        ('70% Completed', '70% Completed'),
        ('Completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    target_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')

    def __str__(self):
        return self.title

class BuyShare(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    price_per_share = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2) # Manual input
    buy_date = models.DateField(default=timezone.now)
    target_date = models.DateField(null=True, blank=True)
    target_holding_period = models.CharField(max_length=100) # e.g., "1 year", "6 months"

    def save(self, *args, **kwargs):
        if self.quantity and self.quantity > 0:
            if self.total_price and not self.price_per_share:
                self.price_per_share = round(self.total_price / self.quantity, 2)
            elif self.price_per_share and not self.total_price:
                self.total_price = self.price_per_share * self.quantity
        
        # Auto-calculate target_date if not provided
        if not self.target_date and self.buy_date and self.target_holding_period:
            import re
            import datetime
            period_str = self.target_holding_period.lower()
            match = re.search(r'(\d+)\s*(day|week|month|year)s?', period_str)
            if match:
                number = int(match.group(1))
                unit = match.group(2)
                
                if unit == 'day':
                    self.target_date = self.buy_date + datetime.timedelta(days=number)
                elif unit == 'week':
                    self.target_date = self.buy_date + datetime.timedelta(weeks=number)
                elif unit == 'month':
                    # Precise month calculation
                    year = self.buy_date.year + (self.buy_date.month + number - 1) // 12
                    month = (self.buy_date.month + number - 1) % 12 + 1
                    # Handle day overflow (e.g., Jan 31 + 1 month -> Feb 28/29)
                    import calendar
                    last_day = calendar.monthrange(year, month)[1]
                    day = min(self.buy_date.day, last_day)
                    self.target_date = datetime.date(year, month, day)
                elif unit == 'year':
                    year = self.buy_date.year + number
                    month = self.buy_date.month
                    import calendar
                    last_day = calendar.monthrange(year, month)[1]
                    day = min(self.buy_date.day, last_day)
                    self.target_date = datetime.date(year, month, day)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Buy {self.company_name} - {self.quantity}"

class SellShare(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    buy_share = models.ForeignKey(BuyShare, on_delete=models.CASCADE)
    sell_price_per_share = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_sold = models.IntegerField()
    sell_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    total_sale_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # Ensure consistency: if total_sale_amount is not set but price is, calculate it.
        # Or if total is set, we might adjust price or just keep as is?
        # User wants Total to be the truth.
        # But we also have price_per_share field.
        # We should calculate the missing one if possible.
        if self.total_sale_amount and not self.sell_price_per_share and self.quantity_sold:
            self.sell_price_per_share = round(self.total_sale_amount / self.quantity_sold, 2)
        elif self.sell_price_per_share and self.quantity_sold and not self.total_sale_amount:
            self.total_sale_amount = self.quantity_sold * self.sell_price_per_share
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sell {self.buy_share.company_name} - {self.quantity_sold}"

class FutureMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    delivery_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    image = models.ImageField(upload_to='future_messages/images/', blank=True, null=True)
    video = models.FileField(upload_to='future_messages/videos/', blank=True, null=True)

    def __str__(self):
        return self.title
