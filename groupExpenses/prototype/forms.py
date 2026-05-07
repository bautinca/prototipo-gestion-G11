from django import forms
from .models import Group

class GroupForm(forms.ModelForm):
    name = forms.CharField(
        max_length=200,
        label='Nombre del grupo',
        error_messages={'required': 'Ingresá un nombre para el grupo'}
    )
    currency = forms.ChoiceField(
        label='Divisa del grupo',
        choices=[('ARS', 'Pesos (ARS)'), ('USD', 'Dólares (USD)'), ('EUR', 'Euros (EUR)')]
    )

    class Meta:
        model = Group
        fields = ['name', 'currency']
