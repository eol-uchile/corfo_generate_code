# Generated by Django 2.2.19 on 2021-04-06 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corfogeneratecode', '0006_corfocodeuser_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corfocodeuser',
            name='created_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
