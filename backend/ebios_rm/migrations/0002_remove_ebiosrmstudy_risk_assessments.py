# Generated by Django 5.1.1 on 2024-12-09 15:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ebios_rm', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ebiosrmstudy',
            name='risk_assessments',
        ),
    ]
