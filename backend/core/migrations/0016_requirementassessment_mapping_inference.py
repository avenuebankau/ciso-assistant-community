# Generated by Django 5.0.6 on 2024-06-27 16:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_requirementmappingset_requirementmapping"),
    ]

    operations = [
        migrations.AddField(
            model_name="requirementassessment",
            name="mapping_inference",
            field=models.JSONField(default=dict, verbose_name="Mapping inference"),
        ),
    ]
