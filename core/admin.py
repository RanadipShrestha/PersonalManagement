from django.contrib import admin
from .models import Todo, Journal, Transaction, LifeGoal, BuyShare, SellShare, FutureMessage,ParticipationClick,MonthlyParticipation

# Register your models here.
@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'created_at']
    search_fields = ['title', 'user__username']

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'date', 'mood']
    list_filter = ['mood', 'date']
    search_fields = ['title', 'content', 'user__username']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'is_expense', 'expense_type', 'date']
    list_filter = ['is_expense', 'expense_type', 'date']
    search_fields = ['notes', 'user__username']

@admin.register(LifeGoal)
class LifeGoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'target_date']
    list_filter = ['status', 'target_date']
    search_fields = ['title', 'description', 'user__username']

@admin.register(BuyShare)
class BuyShareAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'quantity', 'price_per_share', 'total_price', 'buy_date']
    list_filter = ['buy_date']
    search_fields = ['company_name', 'user__username']

@admin.register(SellShare)
class SellShareAdmin(admin.ModelAdmin):
    list_display = ['buy_share', 'user', 'quantity_sold', 'sell_price_per_share', 'total_sale_amount', 'sell_date']
    list_filter = ['sell_date']
    search_fields = ['buy_share__company_name', 'user__username']
    
    def user(self, obj):
        return obj.buy_share.user
    user.short_description = 'User'

@admin.register(FutureMessage)
class FutureMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'delivery_date', 'is_read', 'created_at']
    list_filter = ['delivery_date', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']

admin.site.register(ParticipationClick)
admin.site.register(MonthlyParticipation)
