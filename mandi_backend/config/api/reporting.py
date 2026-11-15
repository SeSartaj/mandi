from apps.reporting import services as reporting
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import filters


class Coverage(APIView):
    def get(self, request):
        return Response(reporting.coverage(request.user, filters(request)))
