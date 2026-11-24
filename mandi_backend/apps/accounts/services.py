from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)


def require(actor, permission):
    if (
        not actor
        or not actor.is_authenticated
        or not actor.is_active
        or not actor.has_perm(permission)
    ):
        raise PermissionDenied("You do not have permission to perform this action.")


def login(email, password):
    email = (email or "").strip().lower()
    matches = list(get_user_model().objects.filter(email__iexact=email)) if email else []
    if len(matches) != 1:
        raise AuthenticationFailed("Invalid email or password.")
    user = authenticate(username=matches[0].username, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid email or password.")
    token, _ = Token.objects.get_or_create(user=user)
    return token, user


def logout(actor):
    Token.objects.filter(user=actor).delete()


def employees(actor):
    require(actor, "accounts.view_user")
    return get_user_model().objects.order_by("display_name", "username")


def get_employee(actor, pk):
    require(actor, "accounts.view_user")
    from django.shortcuts import get_object_or_404

    return get_object_or_404(
        get_user_model().objects.prefetch_related(
            "groups__permissions__content_type", "allowed_checklists"
        ),
        pk=pk,
    )


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
    email = values.pop("email").strip().lower()
    if get_user_model().objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "This email address is already in use."})
    user = get_user_model()(username=email, email=email, **values)
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


def scope_checklists(actor, queryset, field="pk"):
    """Apply the user's checklist allowlist after normal model permissions."""
    if actor.is_superuser or not actor.restrict_checklist_access:
        return queryset
    return queryset.filter(**{f"{field}__in": actor.allowed_checklists.values("pk")})


def require_checklist_access(actor, checklist_id):
    if actor.is_superuser or not actor.restrict_checklist_access:
        return
    if not actor.allowed_checklists.filter(pk=checklist_id).exists():
        raise PermissionDenied("You do not have access to this checklist.")


@transaction.atomic
def update_employee(actor, pk, data):
    from django.shortcuts import get_object_or_404

    from apps.inspections.models import Checklist
    from apps.integrations.models import CollectorGrant

    require(actor, "accounts.change_user")
    user = get_object_or_404(get_user_model().objects.select_for_update(), pk=pk)
    if user.is_superuser and not actor.is_superuser:
        raise PermissionDenied("Only a superuser can manage another superuser.")
    if user.pk == actor.pk and (
        data.get("is_active") is False
        or "group_ids" in data
        or "checklist_ids" in data
        or "restrict_checklist_access" in data
    ):
        raise ValidationError("Ask another administrator to change your own access.")
    if (
        any(
            key in data
            for key in ("is_active", "checklist_ids", "restrict_checklist_access")
        )
        and CollectorGrant.objects.filter(user=user, active=True).exists()
    ):
        raise ValidationError(
            "Revoke this employee's collection access before changing their account or checklist access."
        )
    for key in ("display_name", "position", "is_active", "restrict_checklist_access"):
        if key in data:
            setattr(user, key, data[key])
    if "email" in data:
        email = data["email"].strip().lower()
        if (
            get_user_model()
            .objects.filter(email__iexact=email)
            .exclude(pk=user.pk)
            .exists()
        ):
            raise ValidationError({"email": "This email address is already in use."})
        user.email = email
        # New accounts use the email as their Django username; keep them in sync
        # so admin and CLI tools show the same sign-in identifier.
        user.username = email
    if "password" in data:
        try:
            validate_password(data["password"], user)
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages}) from exc
        user.set_password(data["password"])
    if "group_ids" in data:
        groups = list(
            Group.objects.filter(pk__in=data["group_ids"], name__startswith="Mandi ")
        )
        if len(groups) != len(set(data["group_ids"])):
            raise ValidationError(
                {"group_ids": "Select known Mandi permission groups."}
            )
        user.groups.set(groups)
    if "checklist_ids" in data:
        checklists = list(
            scope_checklists(
                actor, Checklist.objects.filter(pk__in=data["checklist_ids"])
            )
        )
        if len(checklists) != len(set(data["checklist_ids"])):
            raise ValidationError(
                {"checklist_ids": "Select accessible, known checklists."}
            )
        user.allowed_checklists.set(checklists)
    user.save()
    if "password" in data or not user.is_active:
        Token.objects.filter(user=user).delete()
    return user
