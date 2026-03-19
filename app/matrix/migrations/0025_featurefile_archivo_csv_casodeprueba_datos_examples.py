# FeatureFile: CSV opcional para expandir Scenario Outline
# CasoDePrueba: datos_examples (JSON) para filas del CSV

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('matrix', '0024_casodeprueba_scenario_stable_id_featurefile_matriz'),
    ]

    operations = [
        migrations.AddField(
            model_name='featurefile',
            name='archivo_csv',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='csv/',
                verbose_name='CSV de Examples (opcional)',
            ),
        ),
        migrations.AddField(
            model_name='casodeprueba',
            name='datos_examples',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
