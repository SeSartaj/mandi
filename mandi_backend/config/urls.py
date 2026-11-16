from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.http import JsonResponse
from . import api
from .schema import Schema
from .api.checklists import ChecklistDownload
from .api.accounts import EmployeeDetail
from .api.collection import CollectionSync, CollectionSubmissions, CollectionSubmissionDetail, CollectorAccess, CollectionAttachment


def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "service": "mandi"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/checklists/<int:pk>/download/", ChecklistDownload.as_view()),
    path("api/v1/employees/<int:pk>/", EmployeeDetail.as_view()),
    path("api/v1/employees/<int:pk>/collection-access/", CollectorAccess.as_view()),
    path("api/v1/integrations/collection/sync/", CollectionSync.as_view()),
    path("api/v1/integrations/establishments.csv", api.KoboEstablishmentsCsv.as_view()),
    path("api/v1/checklists/<int:pk>/collection-submissions/", CollectionSubmissions.as_view()),
    path("api/v1/establishments/<uuid:establishment_pk>/collection-submissions/", CollectionSubmissions.as_view()),
    path("api/v1/collection-submissions/<int:pk>/attachments/<int:index>/", CollectionAttachment.as_view()),
    path("api/v1/collection-submissions/<int:pk>/", CollectionSubmissionDetail.as_view()),
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
    ("establishments/<uuid:pk>/kobo-submissions/", api.EstablishmentKoboSubmissions),
    ("sources/<str:source>/", api.SourceSearch),
    ("inspections/", api.Inspections),
    ("inspections/<int:pk>/", api.InspectionDetail),
    ("inspections/<int:pk>/approve/", api.Approve),
    ("integrations/ingest/", api.Ingest),
    ("integrations/establishment-choices/", api.Choices),
    ("integrations/kobo/sync/", api.KoboSync),
    ("integrations/kobo/establishments.csv", api.KoboEstablishmentsCsv),
    ("checklists/", api.Checklists),
    ("checklists/metadata/", api.ChecklistMetadata),
    ("checklists/<int:pk>/", api.ChecklistDetail),
    ("checklists/<int:pk>/submissions/", api.ChecklistSubmissions),
    ("checklists/<int:pk>/deploy/", api.ChecklistDeploy),
    ("checklists/<int:pk>/link-kobo/", api.ChecklistLinkKobo),
    ("kobo-submissions/<int:pk>/", api.KoboSubmissionDetail),
    (
        "kobo-submissions/<int:pk>/attachments/<int:index>/",
        api.KoboSubmissionAttachment,
    ),
    ("reports/coverage/", api.Coverage),
]:
    urlpatterns.append(path("api/v1/" + route, view.as_view()))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
