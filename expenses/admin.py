from django.contrib import admin
from .models import Expense, PocketMoney

class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'date', 'user')
    list_filter = ('category', 'user')
    search_fields = ('category', 'note', 'user__username')
    fields = ('user', 'amount', 'category', 'date', 'note')

class PocketMoneyAdmin(admin.ModelAdmin):
    list_display = ('amount', 'date_received', 'user')
    list_filter = ('user',)
    search_fields = ('note', 'user__username')
    fields = ('user', 'amount', 'date_received', 'note')

admin.site.register(Expense, ExpenseAdmin)
admin.site.register(PocketMoney, PocketMoneyAdmin)
