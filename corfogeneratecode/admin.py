from django.contrib import admin
from .models import CorfoCodeUser

# Register your models here.


class CorfoCodeUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'code')
    search_fields = ['user', 'course', 'code']
    ordering = ['-user']

admin.site.register(CorfoCodeUser, CorfoCodeUserAdmin)
