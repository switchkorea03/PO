from django.contrib import admin
from django.urls import path, include
from accounts import views
urlpatterns=[path("admin/",admin.site.urls),path("accounts/",include("django.contrib.auth.urls")),path("orders/",views.order_list),path("calendar/",views.work_calendar),path("settings/notices/",views.notice_settings),path("notices/history/",views.notice_settings)]
