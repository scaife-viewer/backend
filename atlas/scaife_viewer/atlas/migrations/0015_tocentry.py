# Generated by Django 2.2.26 on 2023-07-03 04:33

from django.db import migrations, models
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ("scaife_viewer_atlas", "0014_merge_20230406_1139"),
    ]

    operations = [
        migrations.CreateModel(
            name="TOCEntry",
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
                ("path", models.CharField(max_length=255, unique=True)),
                ("depth", models.PositiveIntegerField()),
                ("numchild", models.PositiveIntegerField(default=0)),
                ("urn", models.CharField(max_length=255, unique=True)),
                ("label", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("uri", models.CharField(max_length=255)),
                (
                    "cts_relations",
                    sortedm2m.fields.SortedManyToManyField(
                        help_text=None,
                        related_name="toc_entries",
                        to="scaife_viewer_atlas.Node",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
    ]
