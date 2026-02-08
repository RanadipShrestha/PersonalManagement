from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Todo, Journal, Transaction, LifeGoal, BuyShare, SellShare, FutureMessage

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class TodoForm(forms.ModelForm):
    class Meta:
        model = Todo
        fields = ['title', 'is_completed']

class JournalForm(forms.ModelForm):
    class Meta:
        model = Journal
        fields = ['title', 'content', 'mood']

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'amount', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'amount', 'notes', 'expense_type']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class LifeGoalForm(forms.ModelForm):
    class Meta:
        model = LifeGoal
        fields = ['title', 'description', 'target_date']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LifeGoalUpdateForm(forms.ModelForm):
    class Meta:
        model = LifeGoal
        fields = ['title', 'description', 'target_date', 'status']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
        }

class BuyShareForm(forms.ModelForm):
    class Meta:
        model = BuyShare
        fields = ['company_name', 'price_per_share', 'quantity', 'total_price', 'buy_date', 'target_holding_period']
        widgets = {
            'buy_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price_per_share'].required = False
        self.fields['total_price'].required = False

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        price_per_share = cleaned_data.get('price_per_share')
        total_price = cleaned_data.get('total_price')

        if quantity and quantity > 0:
            # Logic: Prioritize Total Price if both or only Total is present (to fix user issues like 1100 total vs 101 price)
            
            if total_price:
                 # Recalculate price per share to match total exactly
                 cleaned_data['price_per_share'] = round(total_price / quantity, 2)
            
            elif price_per_share and not total_price:
                 # Calculate total from price
                 cleaned_data['total_price'] = price_per_share * quantity
        else:
             if quantity is not None and quantity <= 0:
                 self.add_error('quantity', "Quantity must be greater than 0.")

        if not cleaned_data.get('price_per_share') and not cleaned_data.get('total_price'):
             raise forms.ValidationError("Please provide either Price per Share OR Total Price.")
        
        return cleaned_data

class SellShareForm(forms.ModelForm):
    total_sale_amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False, label="Total Sale Amount")

    class Meta:
        model = SellShare
        fields = ['buy_share', 'sell_price_per_share', 'quantity_sold', 'total_sale_amount', 'sell_date', 'notes']
        widgets = {
            'sell_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['buy_share'].queryset = BuyShare.objects.filter(user=user)
        # Make sell_price_per_share optional since we can calculate it from total_sale_amount
        self.fields['sell_price_per_share'].required = False

    def clean(self):
        cleaned_data = super().clean()
        buy_share = cleaned_data.get('buy_share')
        quantity_sold = cleaned_data.get('quantity_sold')
        sell_price_per_share = cleaned_data.get('sell_price_per_share')
        total_sale_amount = cleaned_data.get('total_sale_amount')

        # Logic: 
        # 1. If BOTH are provided, Validate consistency.
        # 2. If only Total is provided, Calculate Price.
        # 3. If only Price is provided, Calculate Total.

        if quantity_sold and quantity_sold > 0:
            # Logic: 
            # If ONLY Total is provided, Calculate Price.
            # If ONLY Price is provided, Calculate Total.
            # If BOTH are provided, Save BOTH as is (User override).

            if total_sale_amount and not sell_price_per_share:
                cleaned_data['sell_price_per_share'] = round(total_sale_amount / quantity_sold, 2)
                
            elif sell_price_per_share and not total_sale_amount:
                cleaned_data['total_sale_amount'] = sell_price_per_share * quantity_sold
        else:
             if quantity_sold is not None and quantity_sold <= 0:
                  self.add_error('quantity_sold', "Quantity must be greater than 0.")

        
        # Ensure we have data
        if not cleaned_data.get('total_sale_amount') and not cleaned_data.get('sell_price_per_share'):
             raise forms.ValidationError("Please provide either Sell Price per Share OR Total Sale Amount.")

        if buy_share and quantity_sold:
            # Calculate currently remaining shares
            from django.db.models import Sum
            from django.db.models.functions import Coalesce
            
            # Use filters to exclude current instance when updating to avoid double counting
            existing_sold_qs = buy_share.sellshare_set.all()
            if self.instance.pk:
                existing_sold_qs = existing_sold_qs.exclude(pk=self.instance.pk)

            total_sold = existing_sold_qs.aggregate(
                total=Coalesce(Sum('quantity_sold'), 0)
            )['total']
            
            remaining = buy_share.quantity - total_sold
            
            if quantity_sold > remaining:
                raise forms.ValidationError(
                    f"You only have {remaining} shares remaining for {buy_share.company_name}."
                )
        return cleaned_data

class FutureMessageForm(forms.ModelForm):
    class Meta:
        model = FutureMessage # We need to import this!
        fields = ['title', 'message', 'delivery_date', 'image', 'video']
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        from django.utils import timezone
        if delivery_date <= timezone.now().date():
             raise forms.ValidationError("Delivery date must be in the future.")
        return delivery_date
