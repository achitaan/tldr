from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('study','0001_initial')]
    operations=[migrations.RunSQL('CREATE VIRTUAL TABLE IF NOT EXISTS study_page_fts USING fts5(text, course UNINDEXED)', 'DROP TABLE IF EXISTS study_page_fts')]
