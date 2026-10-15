from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('study', '0003_job_worker_active')]
    operations = [
        migrations.AddField(model_name='source', name='source_url', field=models.URLField(blank=True, max_length=2048)),
        migrations.AddField(model_name='source', name='fetched_url', field=models.URLField(blank=True, max_length=2048)),
        migrations.AddField(model_name='source', name='fetched_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='source', name='extraction_notes', field=models.TextField(blank=True)),
    ]
