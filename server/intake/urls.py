from django.urls import path
from . import views
urlpatterns=[path('sources/<uuid:source_id>/preview/',views.source_preview),path('sources/<uuid:source_id>/preview-image/',views.source_preview_image)]
urlpatterns += [path('intake/upload/',views.upload),path('intake/jobs/<uuid:job_id>/',views.job_status),path('sources/<uuid:source_id>/download/',views.source_download),path('intake/<uuid:draft_id>/review/',views.review),path('intake/<uuid:draft_id>/confirm/',views.confirm)]
