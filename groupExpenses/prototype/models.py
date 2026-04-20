from django.db import models
from decimal import Decimal

CURRENCY_CHOICES = [
    ('ARS', 'Pesos (ARS)'),
    ('USD', 'Dólares (USD)'),
    ('EUR', 'Euros (EUR)'),
]

class Group(models.Model):
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='ARS')
    members = models.JSONField(default=list)
    updated = models.DateField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total(self):
        from django.db.models import Sum
        result = self.expense_set.aggregate(Sum('amount'))['amount__sum']
        return result if result is not None else Decimal('0')


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    paid_by = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)

    def __str__(self):
        return f"{self.paid_by}: {self.amount}"
