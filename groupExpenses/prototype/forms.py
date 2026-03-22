from .models import Group
from django.forms import ModelForm

# Formulario creacion grupo
class GroupForm(ModelForm):
  class Meta:
    model = Group
    fields = ['name', 'currency']