# Generated by Django 2.2.26 on 2022-04-15 05:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0010_token_annotations"),
    ]

    operations = [
        migrations.AddField(
            model_name="citation",
            name="entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="citations",
                to="scaife_viewer_atlas.DictionaryEntry",
            ),
        ),
        migrations.AlterField(
            model_name="citation",
            name="sense",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="citations",
                to="scaife_viewer_atlas.Sense",
            ),
        ),
    ]
