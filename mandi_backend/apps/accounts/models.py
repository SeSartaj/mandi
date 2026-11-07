from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.display_name or self.username
