# Generated by Django 2.2.24 on 2021-11-29 11:28

from django.db import migrations, models
import django.db.models.deletion
import django_jsonfield_backport.models


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0009_text_annotation_collection"),
    ]

    operations = [
        migrations.CreateModel(
            name="TokenAnnotationCollection",
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
                ("urn", models.CharField(max_length=255, unique=True)),
                ("label", models.CharField(max_length=255)),
                (
                    "metadata",
                    django_jsonfield_backport.models.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
            ],
        ),
        migrations.RemoveField(model_name="token", name="case",),
        migrations.RemoveField(model_name="token", name="gloss",),
        migrations.RemoveField(model_name="token", name="lemma",),
        migrations.RemoveField(model_name="token", name="mood",),
        migrations.RemoveField(model_name="token", name="part_of_speech",),
        migrations.RemoveField(model_name="token", name="tag",),
        migrations.CreateModel(
            name="TokenAnnotation",
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
                (
                    "data",
                    django_jsonfield_backport.models.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="annotations",
                        to="scaife_viewer_atlas.TokenAnnotationCollection",
                    ),
                ),
                (
                    "token",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="annotations",
                        to="scaife_viewer_atlas.Token",
                    ),
                ),
            ],
        ),
    ]
