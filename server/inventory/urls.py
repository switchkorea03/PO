from django.urls import path
from .views import index

urlpatterns=[path('inventory/',index,name='inventory')]
