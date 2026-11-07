from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.http import JsonResponse
from . import api
from .schema import Schema


def health(request):
    return JsonResponse({"status": "ok", "service": "mandi"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/v1/schema/", Schema.as_view()),
]
for route, view in [
    ("auth/login/", api.Login),
    ("auth/me/", api.Me),
    ("auth/logout/", api.Logout),
    ("employees/", api.Employees),
    ("permission-groups/", api.PermissionGroups),
    ("establishments/", api.Establishments),
    ("establishments/<uuid:pk>/", api.EstablishmentDetail),
    ("establishments/<uuid:pk>/sources/<str:source>/", api.SourceConnection),
    ("sources/<str:source>/", api.SourceSearch),
    ("inspections/", api.Inspections),
    ("inspections/<int:pk>/", api.InspectionDetail),
    ("inspections/<int:pk>/approve/", api.Approve),
    ("integrations/ingest/", api.Ingest),
    ("integrations/establishment-choices/", api.Choices),
    ("checklists/", api.Checklists),
    ("checklists/<int:pk>/", api.ChecklistDetail),
    ("checklists/<int:pk>/deploy/", api.ChecklistDeploy),
    ("reports/coverage/", api.Coverage),
]:
    urlpatterns.append(path("api/v1/" + route, view.as_view()))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
