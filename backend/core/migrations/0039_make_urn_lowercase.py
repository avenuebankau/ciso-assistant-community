# Generated by Django 5.1.1 on 2024-11-23 07:58

# Explain this bug: django.db.transaction.TransactionManagementError: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block.

from django.db import migrations
from django.db.models.functions import Lower


def make_urn_lowercase(apps, schema_editor):
    Threat = apps.get_model("core", "Threat")
    ReferenceControl = apps.get_model("core", "ReferenceControl")
    RiskMatrix = apps.get_model("core", "RiskMatrix")
    Framework = apps.get_model("core", "Framework")
    RequirementNode = apps.get_model("core", "RequirementNode")
    RequirementMappingSet = apps.get_model("core", "RequirementMappingSet")
    StoredLibrary = apps.get_model("core", "StoredLibrary")
    LoadedLibrary = apps.get_model("core", "LoadedLibrary")

    models = [
        Threat,
        ReferenceControl,
        RiskMatrix,
        Framework,
        RequirementMappingSet,
        StoredLibrary,
        LoadedLibrary,
    ]
    for model in models:
        model.objects.filter(urn__isnull=False).update(urn=Lower("urn"))

    RequirementNode.objects.filter(urn__isnull=False).update(urn=Lower("urn"))
    RequirementNode.objects.filter(parent_urn__isnull=False).update(
        parent_urn=Lower("parent_urn")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0038_asset_disaster_recovery_objectives_and_more"),
    ]

    operations = [migrations.RunPython(make_urn_lowercase)]
