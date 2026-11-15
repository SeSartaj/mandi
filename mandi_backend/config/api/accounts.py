from apps.accounts import services as accounts
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .common import paginated, session, validated
from .serializers import EmployeeInput, LoginInput, UserSerializer


class PermissionGroups(APIView):
    def get(self, request):
        return Response(
            [
                {
                    "id": group.pk,
                    "name": group.name,
                    "permissions": [
                        f"{p.content_type.app_label}.{p.codename}"
                        for p in group.permissions.all()
                    ],
                }
                for group in accounts.permission_groups(request.user)
            ]
        )


class Login(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    def post(self, request):
        token, user = accounts.login(**validated(LoginInput, request.data))
        return Response({"token": token.key, **session(user)})


class Me(APIView):
    def get(self, request):
        return Response(session(request.user))


class Logout(APIView):
    def post(self, request):
        accounts.logout(request.user)
        return Response(status=204)


class Employees(APIView):
    def get(self, request):
        return paginated(request, accounts.employees(request.user), UserSerializer)

    def post(self, request):
        return Response(
            UserSerializer(
                accounts.create_employee(
                    request.user, validated(EmployeeInput, request.data)
                )
            ).data,
            status=201,
        )
