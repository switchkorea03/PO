from django.urls import path
from . import views
urlpatterns=[path('settings/notices/',views.settings_page),path('notices/history/',views.history)]
