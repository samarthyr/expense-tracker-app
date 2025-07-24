# expenses/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='expenses/login.html'), name='login'),
    path('', views.welcome, name='welcome'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('add/', views.add_expense, name='add_expense'),
    path('edit/<int:id>/', views.edit_expense, name='edit_expense'),
    path('pocket-money/add/', views.add_pocket_money, name='add_pocket_money'),
    path('pocket-money/', views.view_pocket_money, name='view_pocket_money'),
    path('pocket-money/edit/<int:id>/', views.edit_pocket_money, name='edit_pocket_money'),
    path('expense/edit/<int:id>/', views.edit_expense, name='edit_expense'),
    path('expense/delete/<int:id>/', views.delete_expense, name='delete_expense'),
    path('weekly/', views.weekly_expenses, name='weekly_expenses'),
    path('monthly/', views.monthly_expenses, name='monthly_expenses'),
    path('monthly/', views.monthly_overview, name='monthly_overview'),
    path('monthly/<int:year>/<int:month>/', views.monthly_detail, name='monthly_detail'),
    path('download_monthly_expenses/', views.download_monthly_expenses, name='download_monthly_expenses'),
    path('analysis/', views.analysis, name='analysis'),
    path('import-statement/', views.import_statement, name='import_statement'),
]
