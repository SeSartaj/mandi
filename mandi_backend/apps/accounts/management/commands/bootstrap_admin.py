import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial administrator once; never reset an existing password."

    def handle(self, **options):
        username = os.environ["MANDI_ADMIN_USERNAME"]
        if get_user_model().objects.filter(username=username).exists():
            return
        password = os.environ["MANDI_ADMIN_PASSWORD"]
        validate_password(password)
        get_user_model().objects.create_superuser(
            username=username,
            email=os.environ.get("MANDI_ADMIN_EMAIL", ""),
            password=password,
        )
        self.stdout.write("Initial Mandi administrator created.")
