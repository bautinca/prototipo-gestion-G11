from django import forms
from .models import Group

class GroupForm(forms.ModelForm):
    name = forms.CharField(
        max_length=200,
        error_messages={'required': 'Ingresá un nombre para el grupo'}
    )

    class Meta:
        model = Group
        fields = ['name', 'currency']
