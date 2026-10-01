import django.db.models.deletion
from django.db import migrations, models


def seed_current_status(apps, schema_editor):
    Application = apps.get_model("applications", "Application")
    History = apps.get_model("applications", "ApplicationStatusHistory")
    database = schema_editor.connection.alias
    for application in Application.objects.using(database).iterator():
        History.objects.using(database).create(
            application_id=application.pk,
            status=application.status,
            previous_status="",
            is_baseline=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0004_application_owner_emailmailbox_incomingemail'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.CharField(choices=[('Saved', 'Saved'), ('Applied', 'Applied'), ('Assessment', 'Assessment'), ('Interview', 'Interview (unspecified stage)'), ('First Interview', 'First Interview'), ('Second Interview', 'Second Interview'), ('Final Interview', 'Final Interview'), ('Rejected', 'Rejected'), ('Offer', 'Offer')], default='Saved', max_length=20),
        ),
        migrations.AlterField(
            model_name='incomingemail',
            name='suggested_status',
            field=models.CharField(blank=True, choices=[('Saved', 'Saved'), ('Applied', 'Applied'), ('Assessment', 'Assessment'), ('Interview', 'Interview (unspecified stage)'), ('First Interview', 'First Interview'), ('Second Interview', 'Second Interview'), ('Final Interview', 'Final Interview'), ('Rejected', 'Rejected'), ('Offer', 'Offer')], max_length=20),
        ),
        migrations.CreateModel(
            name='ApplicationStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_status', models.CharField(blank=True, max_length=20)),
                ('status', models.CharField(choices=[('Saved', 'Saved'), ('Applied', 'Applied'), ('Assessment', 'Assessment'), ('Interview', 'Interview (unspecified stage)'), ('First Interview', 'First Interview'), ('Second Interview', 'Second Interview'), ('Final Interview', 'Final Interview'), ('Rejected', 'Rejected'), ('Offer', 'Offer')], max_length=20)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('is_baseline', models.BooleanField(default=False)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='applications.application')),
            ],
            options={
                'verbose_name_plural': 'application status history',
                'ordering': ['recorded_at', 'id'],
            },
        ),
        migrations.RunPython(seed_current_status, migrations.RunPython.noop),
    ]
