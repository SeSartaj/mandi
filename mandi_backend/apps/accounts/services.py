from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)
from rest_framework.authtoken.models import Token
from django.db import transaction


def require(actor, permission):
    if (
        not actor
        or not actor.is_authenticated
        or not actor.is_active
        or not actor.has_perm(permission)
    ):
        raise PermissionDenied("You do not have permission to perform this action.")


def login(username, password):
    user = authenticate(username=username, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid username or password.")
    token, _ = Token.objects.get_or_create(user=user)
    return token, user


def logout(actor):
    Token.objects.filter(user=actor).delete()


def employees(actor):
    require(actor, "accounts.view_user")
    return get_user_model().objects.order_by("display_name", "username")


@transaction.atomic
def create_employee(actor, data):
    require(actor, "accounts.add_user")
    values = dict(data)
    password = values.pop("password")
    group_ids = values.pop("group_ids", [])
    if group_ids:
        require(actor, "accounts.change_user")
    groups = list(Group.objects.filter(pk__in=group_ids, name__startswith="Mandi "))
    if len(groups) != len(set(group_ids)):
        raise ValidationError({"group_ids": "Select known Mandi permission groups."})
    if get_user_model().objects.filter(username=values["username"]).exists():
        raise ValidationError({"username": "This username is already in use."})
    user = get_user_model()(**values)
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from exc
    user.set_password(password)
    user.save()
    user.groups.set(groups)
    return user


def permission_groups(actor):
    require(actor, "auth.view_group")
    return (
        Group.objects.filter(name__startswith="Mandi ")
        .prefetch_related("permissions__content_type")
        .order_by("name")
    )
