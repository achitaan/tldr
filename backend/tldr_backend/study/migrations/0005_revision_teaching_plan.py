from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('study', '0004_source_web_provenance')]
    operations = [
        migrations.AddField(
            model_name='revision',
            name='teaching_plan',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
