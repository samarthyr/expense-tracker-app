from django.db import models
from django.contrib.auth.models import User

# Create your models here.
# expenses/models.py
class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Shopping', 'Shopping'),
        ('Other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    amount = models.FloatField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField()
    note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.month = self.date.month
        self.year = self.date.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category} - ₹{self.amount}"
    
class PocketMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pocketmoney', null=True, blank=True)
    amount = models.FloatField()
    date_received = models.DateField()
    note = models.TextField(blank=True)

    def __str__(self):
        return f"₹{self.amount} on {self.date_received}"

