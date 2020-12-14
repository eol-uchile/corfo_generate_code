from django.contrib.auth.models import User
from django.db import models

from opaque_keys.edx.django.models import CourseKeyField

# Create your models here.


class CorfoCodeUser(models.Model):
    class Meta:
        index_together = [
            ["user", "course"],
        ]
        unique_together = [
            ["user", "course"],
        ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    course = CourseKeyField(max_length=255)

