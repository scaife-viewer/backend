# Generated by Django 2.2.26 on 2022-05-03 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0011_add_entry_citations"),
    ]

    operations = [
        migrations.AddField(
            model_name="dictionaryentry",
            name="headword_normalized_stripped",
            field=models.CharField(
                blank=True, db_index=True, max_length=255, null=True
            ),
        ),
        migrations.AlterField(
            model_name="dictionaryentry",
            name="headword",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="dictionaryentry",
            name="headword_normalized",
            field=models.CharField(
                blank=True, db_index=True, max_length=255, null=True
            ),
        ),
    ]