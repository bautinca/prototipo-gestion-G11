from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('group/<str:pk>/', views.group, name='group'),
    path('group/<str:pk>/delete-member/', views.deleteMember, name='delete-member'),
    path('group/<str:pk>/update-name/', views.updateName, name='update-name'),
    path('create-group/', views.createGroup, name='create-group'),
    path('update-group/<str:pk>/', views.updateGroup, name='update-group'),
]
