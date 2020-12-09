from django.contrib.auth.models import User
from django.db import models

from opaque_keys.edx.django.models import CourseKeyField

# Create your models here.


class CorfoCodeUser(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=False,
        null=False, db_index=True)
    code = models.CharField(max_length=20)
    course = CourseKeyField(max_length=255)

