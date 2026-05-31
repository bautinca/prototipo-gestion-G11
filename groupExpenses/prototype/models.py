from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

CURRENCY_CHOICES = [
    ('ARS', 'Pesos (ARS)'),
    ('USD', 'Dólares (USD)'),
    ('EUR', 'Euros (EUR)'),
]

class Group(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='ARS')
    members = models.ManyToManyField(User, related_name='member_groups', blank=True)
    updated = models.DateField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total(self):
        from django.db.models import Sum
        result = self.expense_set.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum']
        return result if result is not None else Decimal('0')


class Expense(models.Model):
    TRANSACTION_CHOICES = [
        ('expense', 'Gasto'),
        ('settlement', 'Liquidación'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    paid_by = models.CharField(max_length=200)
    paid_to = models.CharField(max_length=200, blank=True, null=True)
    transaction_type = models.CharField(max_length=12, choices=TRANSACTION_CHOICES, default='expense')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    participants = models.JSONField(default=list)

    def __str__(self):
        if self.transaction_type == 'settlement' and self.paid_to:
            return f"{self.paid_by} → {self.paid_to}: {self.amount}"
        return f"{self.paid_by}: {self.amount}"


class GroupInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptada'),
        ('declined', 'Rechazada'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_invitations')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created = models.DateTimeField(auto_now_add=True)
    responded = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('group', 'invited_user')
        ordering = ['-created']

    def __str__(self):
        return f"Invitación de {self.invited_by} a {self.invited_user} para {self.group} ({self.status})"
