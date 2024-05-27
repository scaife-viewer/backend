# Generated by Django 2.2.17 on 2021-09-13 11:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0007_hookset_for_text_annotation_kinds"),
    ]

    operations = [
        migrations.CreateModel(
            name="NamedEntityCollection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("label", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "data",
                    models.JSONField(
                        blank=True, default=dict
                    ),
                ),
                (
                    "urn",
                    models.CharField(
                        help_text="urn:cite2:<site>:named_entity_collection.atlas_v1",
                        max_length=255,
                        unique=True,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="namedentity",
            name="collection",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="entities",
                to="scaife_viewer_atlas.NamedEntityCollection",
            ),
            preserve_default=False,
        ),
    ]
