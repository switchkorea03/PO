from django.urls import path
from . import views
urlpatterns=[path("calendar/",views.calendar_page,name="calendar"),path("api/calendar/",views.calendar_api),path("tasks/<uuid:task_id>/",views.task_detail,name="task-detail"),path("tasks/<uuid:task_id>/move/",views.task_move),path("tasks/<uuid:task_id>/review/",views.task_review),path("substeps/<uuid:substep_id>/check/",views.substep_check)]
