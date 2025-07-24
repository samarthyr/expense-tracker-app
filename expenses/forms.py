# expenses/forms.py
from django import forms
from .models import Expense

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'category', 'date', 'note']

from .models import PocketMoney

class PocketMoneyForm(forms.ModelForm):
    class Meta:
        model = PocketMoney
        fields = ['amount', 'date_received', 'note']

