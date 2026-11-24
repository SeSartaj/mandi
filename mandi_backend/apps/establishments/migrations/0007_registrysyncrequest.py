from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("establishments", "0006_merge_registration_into_licensing"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrySyncRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("done", "Done"), ("failed", "Failed")], default="pending", max_length=20)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("result", models.JSONField(default=dict)),
                ("error", models.CharField(blank=True, max_length=250)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sync_requests", to="establishments.externalsystem")),
            ],
            options={"ordering": ["requested_at"]},
        ),
        migrations.AddConstraint(
            model_name="registrysyncrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("state__in", ["pending", "running"])), fields=("source",), name="one_active_registry_sync_request"),
        ),
    ]
