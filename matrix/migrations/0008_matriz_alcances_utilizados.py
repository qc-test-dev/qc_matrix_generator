# Generated by Django 5.1.7 on 2025-05-19 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matrix', '0007_ticketporlevantar_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='matriz',
            name='alcances_utilizados',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
