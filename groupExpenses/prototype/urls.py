from django.urls import path
from . import views

urlpatterns = [
  path("", views.home, name="home"), # URL home page
  path("group/<str:pk>/", views.group, name="group"), # URL page group
  path("create-group/", views.createGroup, name="create-group"), # URL creacion grupo
  path("update-group/<str:pk>/", views.updateGroup, name="update-group") # URL editar grupo
]