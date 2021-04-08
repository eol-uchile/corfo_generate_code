from django.contrib.auth.models import User
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField

# Create your models here.

class CorfoCodeMappingContent(models.Model):
    id_content = models.IntegerField(unique=True, default=0)
    content = models.CharField(max_length=255, default="")

    def __str__(self):
        return '(%s) -> %s' % (self.id_content, self.content)

class CorfoCodeInstitution(models.Model):
    id_institution = models.IntegerField(unique=True, default=0)
    institution = models.CharField(max_length=255, default="")

    def __str__(self):
        return '(%s) -> %s' % (self.id_institution, self.institution)

class CorfoCodeUser(models.Model):
    class Meta:
        index_together = [
            ["user", "mapping_content"],
        ]
        unique_together = [
            ["user", "mapping_content"],
        ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now=True, blank=True)
    mapping_content = models.ForeignKey(
        CorfoCodeMappingContent,
        on_delete=models.CASCADE,
        related_name="mapping_content",
        blank=True,
        null=True
    )