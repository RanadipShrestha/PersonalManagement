from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('', views.DashboardView.as_view(), name='home'),

    # Todo
    path('todos/', views.TodoListView.as_view(), name='todo-list'),
    path('todos/new/', views.TodoCreateView.as_view(), name='todo-create'),
    path('todos/<int:pk>/update/', views.TodoUpdateView.as_view(), name='todo-update'),
    path('todos/<int:pk>/toggle/', views.toggle_todo, name='todo-toggle'),

    # Journal
    path('journal/', views.JournalListView.as_view(), name='journal-list'),
    path('journal/new/', views.JournalCreateView.as_view(), name='journal-create'),
    path('journal/<int:pk>/', views.JournalDetailView.as_view(), name='journal-detail'),

    # Finance
    path('finance/', views.TransactionListView.as_view(), name='transaction-list'),
    path('finance/income/new/', views.IncomeCreateView.as_view(), name='income-create'),
    path('finance/expense/new/', views.ExpenseCreateView.as_view(), name='expense-create'),
    path('finance/income/<int:pk>/update/', views.IncomeUpdateView.as_view(), name='income-update'),
    path('finance/expense/<int:pk>/update/', views.ExpenseUpdateView.as_view(), name='expense-update'),
    path('finance/transaction/<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='transaction-delete'),

    # Life Goals
    path('goals/', views.LifeGoalListView.as_view(), name='lifegoal-list'),
    path('goals/new/', views.LifeGoalCreateView.as_view(), name='lifegoal-create'),
    path('goals/<int:pk>/update/', views.LifeGoalUpdateView.as_view(), name='lifegoal-update'),
    path('goals/<int:pk>/delete/', views.LifeGoalDeleteView.as_view(), name='lifegoal-delete'),

    # Share Management
    path('share/', views.ShareDashboardView.as_view(), name='share-dashboard'),
    path('share/buy/new/', views.BuyShareCreateView.as_view(), name='buyshare-create'),
    path('share/buy/<int:pk>/update/', views.BuyShareUpdateView.as_view(), name='buyshare-update'),
    path('share/buy/<int:pk>/delete/', views.BuyShareDeleteView.as_view(), name='buyshare-delete'),
    path('share/sell/new/', views.SellShareCreateView.as_view(), name='sellshare-create'),
    path('share/sell/<int:pk>/update/', views.SellShareUpdateView.as_view(), name='sellshare-update'),
    path('share/sell/<int:pk>/delete/', views.SellShareDeleteView.as_view(), name='sellshare-delete'),
]
