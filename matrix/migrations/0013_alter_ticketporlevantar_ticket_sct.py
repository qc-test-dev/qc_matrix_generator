# Generated by Django 5.1.7 on 2025-05-28 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matrix', '0012_casodeprueba_tester'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketporlevantar',
            name='ticket_SCT',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
