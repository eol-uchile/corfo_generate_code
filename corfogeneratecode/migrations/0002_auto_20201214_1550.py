# Generated by Django 2.2.13 on 2020-12-14 15:50

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('corfogeneratecode', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='corfocodeuser',
            unique_together={('user', 'course')},
        ),
        migrations.AlterIndexTogether(
            name='corfocodeuser',
            index_together={('user', 'course')},
        ),
    ]
