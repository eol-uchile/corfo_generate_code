# Generated by Django 2.2.19 on 2021-04-06 15:11

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corfogeneratecode', '0005_auto_20210304_1351'),
    ]

    operations = [
        migrations.AddField(
            model_name='corfocodeuser',
            name='created_at',
            field=models.DateTimeField(blank=True, default=datetime.datetime.now),
        ),
    ]
