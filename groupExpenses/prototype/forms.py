from django import forms
from .models import Group

class GroupForm(forms.ModelForm):
    name = forms.CharField(
        max_length=200,
        label='Nombre del grupo',
        error_messages={'required': 'Ingresá un nombre para el grupo'}
    )
    description = forms.CharField(
        max_length=300,
        required=False,
        label='Descripción (opcional)',
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej: gastos del viaje a Bariloche'})
    )
    currency = forms.ChoiceField(
        label='Divisa del grupo',
        choices=[('ARS', 'Pesos (ARS)'), ('USD', 'Dólares (USD)'), ('EUR', 'Euros (EUR)')]
    )

    class Meta:
        model = Group
        fields = ['name', 'description', 'currency']
