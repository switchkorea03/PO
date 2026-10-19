from django.contrib import admin
from django.urls import path,include
from django.shortcuts import redirect
from accounts import views
urlpatterns=[path("",lambda request:redirect("/calendar/")),path("admin/",admin.site.urls),path("accounts/",include("django.contrib.auth.urls")),path("",include("orders.urls")),path("",include("work.urls")),path("",include("intake.urls")),path("",include("notices.urls"))]
