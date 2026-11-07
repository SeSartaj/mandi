from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inspections", "0005_checklist_created_at_checklist_created_by_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="checklist",
            name="kobo_asset_uid",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="checklist",
            name="kobo_deployment_status",
            field=models.CharField(
                choices=[
                    ("not_deployed", "Not deployed"),
                    ("deploying", "Deploying"),
                    ("deployed", "Deployed"),
                    ("failed", "Deployment failed"),
                ],
                default="not_deployed",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="checklist",
            name="kobo_deployment_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="checklist",
            name="kobo_deployed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="checklist",
            name="kobo_deployed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
