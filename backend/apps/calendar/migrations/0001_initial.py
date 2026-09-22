from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('prescriptions', '0002_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='GoogleCalendarCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_data', models.TextField()),
                ('calendar_id', models.CharField(default='primary', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='google_calendar_credential',
                                              to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MedicationCalendarEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=255)),
                ('fingerprint', models.CharField(max_length=64)),
                ('calendar_id', models.CharField(default='primary', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               to='prescriptions.medicine')),
                ('prescription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   to='prescriptions.prescription')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='medication_calendar_events',
                                           to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='medicationcalendarevent',
            constraint=models.UniqueConstraint(fields=('user', 'fingerprint'),
                                               name='unique_medication_calendar_fingerprint'),
        ),
    ]
