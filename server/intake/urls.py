from django.urls import path
from . import views,ai_views
urlpatterns_ai=[path('intake/<uuid:draft_id>/gemini/',ai_views.analyze),path('intake/<uuid:draft_id>/gemini/<uuid:review_id>/apply/',ai_views.apply)]
urlpatterns=[path('sources/<uuid:source_id>/preview/',views.source_preview),path('sources/<uuid:source_id>/preview-image/',views.source_preview_image)]
urlpatterns += [path('intake/upload/',views.upload),path('intake/jobs/<uuid:job_id>/',views.job_status),path('sources/<uuid:source_id>/download/',views.source_download),path('intake/<uuid:draft_id>/review/',views.review),path('intake/<uuid:draft_id>/confirm/',views.confirm)]
urlpatterns += urlpatterns_ai
