# Generated by Django 2.2.26 on 2022-10-18 04:30

from django.db import migrations, models
import django.db.models.deletion
import django_jsonfield_backport.models


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0012_add_additional_headword_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="GrammaticalEntryCollection",
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
                    django_jsonfield_backport.models.JSONField(
                        blank=True, default=dict
                    ),
                ),
                (
                    "urn",
                    models.CharField(
                        help_text="urn:cite2:<site>:grammatical_entry_collection.atlas_v1",
                        max_length=255,
                        unique=True,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GrammaticalEntry",
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
                    django_jsonfield_backport.models.JSONField(
                        blank=True, default=dict
                    ),
                ),
                (
                    "idx",
                    models.IntegerField(
                        blank=True, help_text="0-based index", null=True
                    ),
                ),
                ("urn", models.CharField(max_length=255, unique=True)),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="scaife_viewer_atlas.GrammaticalEntryCollection",
                    ),
                ),
                (
                    "tokens",
                    models.ManyToManyField(
                        related_name="grammatical_entries",
                        to="scaife_viewer_atlas.Token",
                    ),
                ),
            ],
        ),
    ]
