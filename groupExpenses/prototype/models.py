from django.db import models

# Tabla grupos
class Group(models.Model):
  name = models.CharField()
  currency = models.CharField(default=None)
  members = models.JSONField(default=list)
  total = models.FloatField(default=0)
  updated = models.DateField(auto_now=True)
  created = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.name
