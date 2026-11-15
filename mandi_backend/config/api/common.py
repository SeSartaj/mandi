from rest_framework.pagination import PageNumberPagination

from .serializers import Filters, UserSerializer


class MandiPagination(PageNumberPagination):
    """Shared page size contract for the copied CMS table/pagination controls."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def validated(cls, data, **kwargs):
    s = cls(data=data, **kwargs)
    s.is_valid(raise_exception=True)
    return s.validated_data


def filters(request):
    return validated(
        Filters, {k: v for k, v in request.query_params.items() if v != ""}
    )


def paginated(request, qs, serializer):
    p = MandiPagination()
    return p.get_paginated_response(
        serializer(p.paginate_queryset(qs, request), many=True).data
    )


def session(user):
    return {
        "user": UserSerializer(user).data,
        "permissions": sorted(user.get_all_permissions()),
    }
