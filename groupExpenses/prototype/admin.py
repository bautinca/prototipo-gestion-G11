from django.contrib import admin

# Registro de tablas personalizadas
from .models import Group # Tabla grupos

admin.site.register(Group)
