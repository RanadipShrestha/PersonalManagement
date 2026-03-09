from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib import messages
from django.views.generic import ListView, CreateView, DeleteView, UpdateView, DetailView, TemplateView
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from .forms import CustomUserCreationForm, TodoForm, JournalForm, IncomeForm, ExpenseForm, LifeGoalForm, LifeGoalUpdateForm, BuyShareForm, SellShareForm
from .models import Todo, Journal, Transaction, LifeGoal, BuyShare, SellShare, Memory, MemoryFile, MonthlyParticipation, ParticipationClick, FutureMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# Authentication Views

class MonthlyParticipationView(LoginRequiredMixin, TemplateView):
    template_name = 'core/participation_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get or create participation object
        participation, created = MonthlyParticipation.objects.get_or_create(
            user=user,
            defaults={'current_amount': 1000.00, 'last_processed_date': timezone.now().date().replace(day=1)}
        )
        
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        
        # We only want to process missing months if the account actually existed *before* this month.
        # But wait, we set last_processed_date = current_month_start initially.
        # If it's already current_month_start, the loop `while last_date < current_month_start:` won't run!
        # WHY did it run in the user's local instance?
        # Ah, because `timezone.now().date().replace(day=1)` isn't timezone-aware in the same way, or the DB already had it created from *last month* tests?
        # If the DB already had it created from a previous attempt/bug when `last_processed_date` might have been set to `timezone.now().date()` (which could be the previous month if created before today's 1st)?
        # Let's add a `created_at` field, or simply just ensure the loop works correctly.
        # But we already created it. The exact issue the user faced: "the current should be 1000 not 1500".
        # If they just visited the page for the first time *today* (March), and the DB record was created *just now*, it should be 1000.
        # If it somehow was created last month (Feb), and they visit now, it expects them to have paid in Feb. If they just created it in Feb (but never visited until Mar), it penalizes.
        # To prevent penalizing immediately upon first creation, we should just ensure `created` is handled.
        
        if created:
            # If it was JUST created, don't do any back-calculation. Just save the 1000 and return.
            participation.current_amount = 1000.00
            participation.last_processed_date = current_month_start
            participation.save()
        else:
            last_date = participation.last_processed_date
            temp_amount = float(participation.current_amount)
            # Only process growth if it's NOT a newly created object
            while last_date < current_month_start:
                # Check if user paid in the month of last_date
                was_paid = ParticipationClick.objects.filter(
                    user=user,
                    click_date__year=last_date.year,
                    click_date__month=last_date.month
                ).exists()
                
                if was_paid:
                    temp_amount *= 1.025
                else:
                    temp_amount *= 1.50
                
                # Move to next month
                if last_date.month == 12:
                    last_date = last_date.replace(year=last_date.year + 1, month=1)
                else:
                    last_date = last_date.replace(month=last_date.month + 1)
            
            participation.current_amount = temp_amount
            participation.last_processed_date = current_month_start
            participation.save()
        
        # Check if already paid for CURRENT month
        is_paid_current = ParticipationClick.objects.filter(
            user=user,
            click_date__year=today.year,
            click_date__month=today.month
        ).exists()
        
        context['participation'] = participation
        context['is_paid_today'] = is_paid_current
        
        # Fetch payment history
        history = ParticipationClick.objects.filter(user=user).order_by('-click_date')
        context['history'] = history
        return context

@login_required
def record_participation_click(request):
    user = request.user
    today = timezone.now().date()
    
    # Check if already clicked this month
    already_clicked = ParticipationClick.objects.filter(
        user=user,
        click_date__year=today.year,
        click_date__month=today.month
    ).exists()
    
    
    if not already_clicked:
        # Get current amount
        participation = MonthlyParticipation.objects.get(user=user)
        ParticipationClick.objects.create(user=user, click_date=today, recorded_amount=participation.current_amount)
        messages.success(request, "Payment recorded for this month!")
    else:
        messages.info(request, "You have already recorded your payment for this month.")
        
    return redirect('participation-detail')

@login_required
@require_POST
def unrecord_participation_click(request):
    user = request.user
    today = timezone.now().date()
    
    # Check if clicked this month
    click = ParticipationClick.objects.filter(
        user=user,
        click_date__year=today.year,
        click_date__month=today.month
    ).first()
    
    if click:
        click.delete()
        messages.success(request, "Payment record for this month has been undone.")
    else:
        messages.info(request, "You haven't recorded a payment for this month yet.")
        
    return redirect('participation-detail')

# Authentication Views
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

# Dashboard
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Most Frequent Mood
        from django.db.models import Count
        most_common_mood = Journal.objects.filter(user=user).values('mood').annotate(count=Count('mood')).order_by('-count').first()
        context['most_frequent_mood'] = most_common_mood['mood'] if most_common_mood else "No Data"

        # 2. Todo Completion Percentage
        total_todos = Todo.objects.filter(user=user).count()
        completed_todos = Todo.objects.filter(user=user, is_completed=True).count()
        if total_todos > 0:
            context['todo_completion_percentage'] = int((completed_todos / total_todos) * 100)
        else:
            context['todo_completion_percentage'] = 0
            
        # 3. Total Balance
        transactions = Transaction.objects.filter(user=user)
        total_income = sum(t.amount for t in transactions if not t.is_expense)
        total_expense = sum(t.amount for t in transactions if t.is_expense)
        context['total_balance'] = total_income - total_expense

        # 4. Calendar Year Activity Data (Dot Graph)
        # We will check for Journal entries for each day in the CURRENT YEAR (Jan 1 - Dec 31).
        # Structure: List of objects/dicts: {'date': date_obj, 'has_activity': bool, 'is_future': bool}
        import datetime
        import calendar
        
        today = timezone.now().date()
        current_year = today.year
        
        # Determine number of days in current year
        is_leap = calendar.isleap(current_year)
        days_in_year = 366 if is_leap else 365
        
        # Get start date and end date
        start_date = datetime.date(current_year, 1, 1)
        # end_date = datetime.date(current_year, 12, 31) # Not strictly needed for loop but good context
        
        # Get all dates with journal entries efficiently
        journal_dates = set(Journal.objects.filter(
            user=user, 
            date__year=current_year
        ).values_list('date', flat=True))

        activity_data = []
        future_days_count = 0
        
        for i in range(days_in_year): 
             date = start_date + datetime.timedelta(days=i)
             is_future = date > today
             is_today = date == today
             
             if is_future:
                 future_days_count += 1
                 
             activity_data.append({
                 'date': date,
                 'has_activity': date in journal_dates and not is_future, 
                 'is_future': is_future,
                 'is_today': is_today
             })
        
        context['activity_data'] = activity_data
        context['days_remaining'] = future_days_count
        context['current_year'] = current_year
        
        return context

# Todo Views
class TodoListView(LoginRequiredMixin, ListView):
    model = Todo
    template_name = 'core/todo_list.html'
    context_object_name = 'todos'

    def get_queryset(self):
        # Filter by today's date
        return Todo.objects.filter(user=self.request.user, created_at__date=timezone.now().date()).order_by('-created_at')

class TodoCreateView(LoginRequiredMixin, CreateView):
    model = Todo
    form_class = TodoForm
    template_name = 'core/todo_form.html'
    success_url = reverse_lazy('todo-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Todo created successfully.')
        return super().form_valid(form)

class TodoUpdateView(LoginRequiredMixin, UpdateView):
    model = Todo
    form_class = TodoForm
    template_name = 'core/todo_form.html'
    success_url = reverse_lazy('todo-list')

    def get_queryset(self):
        return Todo.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Todo updated successfully.')
        return super().form_valid(form)

class TodoDeleteView(LoginRequiredMixin, DeleteView):
    model = Todo
    template_name = 'core/todo_confirm_delete.html'
    success_url = reverse_lazy('todo-list')

    def get_queryset(self):
        return Todo.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Todo deleted successfully.')
        return super().delete(request, *args, **kwargs)

@login_required
@require_POST
def toggle_todo(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    todo.is_completed = not todo.is_completed
    todo.save()
    return redirect('todo-list')

# Journal Views
class JournalListView(LoginRequiredMixin, ListView):
    model = Journal
    template_name = 'core/journal_list.html'
    context_object_name = 'journals'

    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user).order_by('-date')

class JournalDetailView(LoginRequiredMixin, DetailView):
    model = Journal
    template_name = 'core/journal_detail.html'

    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user)

class JournalCreateView(LoginRequiredMixin, CreateView):
    model = Journal
    form_class = JournalForm
    template_name = 'core/journal_form.html'
    success_url = reverse_lazy('journal-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.date = timezone.now().date() # Auto-set date
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "You have already created a journal for today.")
            return self.form_invalid(form)

class JournalUpdateView(LoginRequiredMixin, UpdateView):
    model = Journal
    form_class = JournalForm
    template_name = 'core/journal_form.html'
    success_url = reverse_lazy('journal-list')

    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Journal updated successfully.')
        return super().form_valid(form)

class JournalDeleteView(LoginRequiredMixin, DeleteView):
    model = Journal
    template_name = 'core/journal_confirm_delete.html'
    success_url = reverse_lazy('journal-list')

    def get_queryset(self):
        return Journal.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Journal deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Transaction Views
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'core/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transactions = context['transactions']
        total_income = sum(t.amount for t in transactions if not t.is_expense)
        total_expense = sum(t.amount for t in transactions if t.is_expense)
        context['total_income'] = total_income
        context['total_expense'] = total_expense
        context['balance'] = total_income - total_expense
        return context

class IncomeCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = IncomeForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('transaction-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Record Income'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_expense = False
        messages.success(self.request, 'Income recorded successfully.')
        return super().form_valid(form)

class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = ExpenseForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('transaction-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Record Expense'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.is_expense = True
        messages.success(self.request, 'Expense recorded successfully.')
        return super().form_valid(form)

class IncomeUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = IncomeForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('transaction-list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user, is_expense=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Income'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Income updated successfully.')
        return super().form_valid(form)

class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = ExpenseForm
    template_name = 'core/transaction_form.html'
    success_url = reverse_lazy('transaction-list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user, is_expense=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Expense'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully.')
        return super().form_valid(form)

class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    success_url = reverse_lazy('transaction-list')
    template_name = 'core/transaction_confirm_delete.html'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Transaction deleted successfully.')
        return super().delete(request, *args, **kwargs)

# LifeGoal Views
class LifeGoalListView(LoginRequiredMixin, ListView):
    model = LifeGoal
    template_name = 'core/lifegoal_list.html'
    context_object_name = 'goals'

    def get_queryset(self):
        return LifeGoal.objects.filter(user=self.request.user)

class LifeGoalCreateView(LoginRequiredMixin, CreateView):
    model = LifeGoal
    form_class = LifeGoalForm
    template_name = 'core/lifegoal_form.html'
    success_url = reverse_lazy('lifegoal-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Goal created successfully.')
        return super().form_valid(form)

class LifeGoalUpdateView(LoginRequiredMixin, UpdateView):
    model = LifeGoal
    form_class = LifeGoalUpdateForm
    template_name = 'core/lifegoal_form.html'
    success_url = reverse_lazy('lifegoal-list')

    def get_queryset(self):
        return LifeGoal.objects.filter(user=self.request.user)

class LifeGoalDeleteView(LoginRequiredMixin, DeleteView):
    model = LifeGoal
    success_url = reverse_lazy('lifegoal-list')
    template_name = 'core/lifegoal_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Goal deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Share Views
class ShareDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/share_dashboard.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Sum, F
        from django.db.models.functions import Coalesce
        context = super().get_context_data(**kwargs)
        
        # 1. Fetch all buy shares
        # Note: Aggregation with order_by can cause grouping issues in SQLite/Django sometimes.
        # We will calculate remaining quantity safely.
        all_buys = BuyShare.objects.filter(user=self.request.user).order_by('-buy_date')
        
        # Calculate remaining for each
        buy_shares_data = []
        for buy in all_buys:
            sold_qty = buy.sellshare_set.aggregate(total=Coalesce(Sum('quantity_sold'), 0))['total']
            buy.remaining_quantity = buy.quantity - sold_qty
            buy_shares_data.append(buy)
        
        # 2. Split into Current Holdings (Active) and Buy History (All)
        current_holdings = [h for h in buy_shares_data if h.remaining_quantity > 0]
        
        # 3. Calculate Metrics
        total_current_investment = sum(h.remaining_quantity * h.price_per_share for h in current_holdings)
        
        sales = SellShare.objects.filter(user=self.request.user).select_related('buy_share').order_by('-sell_date')
        
        # Use new total_sale_amount field
        total_sales_value = sum(s.total_sale_amount for s in sales)
        
        # Cost of sold shares: quantity_sold * buy_price
        total_cost_of_sold = sum(s.quantity_sold * s.buy_share.price_per_share for s in sales)
        total_realized_pnl = total_sales_value - total_cost_of_sold
        
        context['current_holdings'] = current_holdings
        context['buy_history'] = buy_shares_data
        context['sales'] = sales
        context['total_current_investment'] = total_current_investment
        context['total_realized_pnl'] = total_realized_pnl
        context['total_sales_value'] = total_sales_value
        return context

class BuyShareCreateView(LoginRequiredMixin, CreateView):
    model = BuyShare
    form_class = BuyShareForm
    template_name = 'core/buyshare_form.html'
    success_url = reverse_lazy('share-dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Share purchase recorded.')
        return super().form_valid(form)

class BuyShareUpdateView(LoginRequiredMixin, UpdateView):
    model = BuyShare
    form_class = BuyShareForm
    template_name = 'core/buyshare_form.html'
    success_url = reverse_lazy('share-dashboard')

    def get_queryset(self):
        return BuyShare.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Share holding updated.')
        return super().form_valid(form)

class BuyShareDeleteView(LoginRequiredMixin, DeleteView):
    model = BuyShare
    success_url = reverse_lazy('share-dashboard')
    template_name = 'core/buyshare_confirm_delete.html'

    def get_queryset(self):
        return BuyShare.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Share holding deleted.')
        return super().delete(request, *args, **kwargs)

class SellShareCreateView(LoginRequiredMixin, CreateView):
    model = SellShare
    form_class = SellShareForm
    template_name = 'core/sellshare_form.html'
    success_url = reverse_lazy('share-dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Share sale recorded.')
        return super().form_valid(form)

class SellShareUpdateView(LoginRequiredMixin, UpdateView):
    model = SellShare
    form_class = SellShareForm
    template_name = 'core/sellshare_form.html'
    success_url = reverse_lazy('share-dashboard')

    def get_queryset(self):
        return SellShare.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Share sale updated.')
        return super().form_valid(form)

class SellShareDeleteView(LoginRequiredMixin, DeleteView):
    model = SellShare
    success_url = reverse_lazy('share-dashboard')
    template_name = 'core/sellshare_confirm_delete.html'

    def get_queryset(self):
        return SellShare.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Share sale deleted.')
        return super().delete(request, *args, **kwargs)

# Future Message Views
from .forms import FutureMessageForm

class FutureMessageListView(LoginRequiredMixin, ListView):
    model = FutureMessage
    template_name = 'core/futuremessage_list.html'
    context_object_name = 'messages'

    def get_queryset(self):
        return FutureMessage.objects.filter(user=self.request.user).order_by('delivery_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_messages = self.get_queryset()
        today = timezone.now().date()
        
        context['delivered_messages'] = all_messages.filter(delivery_date__lte=today)
        context['locked_messages'] = all_messages.filter(delivery_date__gt=today)
        return context

class FutureMessageCreateView(LoginRequiredMixin, CreateView):
    model = FutureMessage
    form_class = FutureMessageForm
    template_name = 'core/futuremessage_form.html'
    success_url = reverse_lazy('future-message-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class FutureMessageDetailView(LoginRequiredMixin, DetailView):
    model = FutureMessage
    template_name = 'core/futuremessage_detail.html'

    def get_queryset(self):
        return FutureMessage.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.delivery_date > timezone.now().date():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("This message is locked until {}".format(obj.delivery_date))
        return obj
# Memory Views
from .forms import MemoryForm

class MemoryListView(LoginRequiredMixin, ListView):
    model = Memory
    template_name = 'core/memory_list.html'
    context_object_name = 'memories'

    def get_queryset(self):
        return Memory.objects.filter(user=self.request.user).order_by('-created_at')

class MemoryCreateView(LoginRequiredMixin, CreateView):
    model = Memory
    form_class = MemoryForm
    template_name = 'core/memory_form.html'
    success_url = reverse_lazy('memory-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        files = self.request.FILES.getlist('files')
        for f in files:
            file_type = 'image'
            if f.content_type.startswith('video'):
                file_type = 'video'
            MemoryFile.objects.create(memory=self.object, file=f, file_type=file_type)
        
        messages.success(self.request, 'Memory saved successfully.')
        return response

class MemoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Memory
    template_name = 'core/memory_confirm_delete.html' # Need to create this too or use a generic one
    success_url = reverse_lazy('memory-list')

    def get_queryset(self):
        return Memory.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Memory deleted successfully.')
        return super().delete(request, *args, **kwargs)
