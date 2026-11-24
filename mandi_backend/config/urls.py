from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.http import JsonResponse
from . import api
from .api.establishments import NearbyEstablishments, RegistryCatalog, RegistryImport, RegistryRefresh, RegistryOwnership, RegistrySyncStatus, RegistrySystems, RegistrySystemSync, RegistrySystemFullSync
from .schema import Schema
from .api.checklists import ChecklistDownload
from .api.accounts import EmployeeDetail
from .api.collection import CollectionSync, CollectionSubmissions, CollectionSubmissionDetail, CollectorAccess, CollectionAttachment, CollectionProjects, EntitySync


def health(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "service": "mandi"})


urlpatterns = [
    path("api/v1/establishments/nearby/", NearbyEstablishments.as_view()),
    path("api/v1/registry/sync/", RegistrySyncStatus.as_view()),
    path("api/v1/registry/systems/", RegistrySystems.as_view()),
    path("api/v1/registry/systems/<str:code>/sync/", RegistrySystemSync.as_view()),
    path("api/v1/registry/systems/<str:code>/full-sync/", RegistrySystemFullSync.as_view()),
    path("api/v1/registry/", RegistryCatalog.as_view()),
    path("api/v1/registry/import/", RegistryImport.as_view()),
    path("api/v1/establishments/<uuid:pk>/refresh/", RegistryRefresh.as_view()),
    path("api/v1/establishments/<uuid:pk>/ownership/", RegistryOwnership.as_view()),
    path("admin/", admin.site.urls),
    path("api/v1/checklists/<int:pk>/download/", ChecklistDownload.as_view()),
    path("api/v1/employees/<int:pk>/", EmployeeDetail.as_view()),
    path("api/v1/employees/<int:pk>/collection-access/", CollectorAccess.as_view()),
    path("api/v1/collection/projects/", CollectionProjects.as_view()),
    path("api/v1/integrations/collection/sync/", CollectionSync.as_view()),
    path("api/v1/integrations/entities/sync/", EntitySync.as_view()),
    path("api/v1/odk/projects/", api.OdkProjects.as_view()),
    path("api/v1/odk/projects/<int:project_id>/", api.OdkProjectDetail.as_view()),
    path("api/v1/integrations/establishments.csv", api.EstablishmentsCsv.as_view()),
    path("api/v1/checklists/<int:pk>/collection-submissions/", CollectionSubmissions.as_view()),
    path("api/v1/submissions/", CollectionSubmissions.as_view()),
    path("api/v1/checklists/<int:pk>/versions/", api.ChecklistVersions.as_view()),
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
    ("establishment-types/", api.EstablishmentTypes),
    ("establishment-types/<slug:code>/", api.EstablishmentTypeDetail),
    ("establishments/<uuid:pk>/sources/<str:source>/", api.SourceConnection),
    ("sources/<str:source>/", api.SourceSearch),
    ("integrations/establishment-choices/", api.Choices),
    ("checklists/", api.Checklists),
    ("checklists/metadata/", api.ChecklistMetadata),
    ("checklists/<int:pk>/", api.ChecklistDetail),
    ("checklists/<int:pk>/deploy/", api.ChecklistDeploy),
]:
    urlpatterns.append(path("api/v1/" + route, view.as_view()))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
