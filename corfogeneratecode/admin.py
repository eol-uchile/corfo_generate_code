from django.contrib import admin
from .models import CorfoCodeUser, CorfoCodeMappingContent

# Register your models here.


class CorfoCodeUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'code')
    search_fields = ['user', 'course', 'code']
    ordering = ['-user']

class CorfoCodeMappingContentAdmin(admin.ModelAdmin):
    list_display = ('id_content', 'content')
    search_fields = ['id_content', 'content']
    ordering = ['-id_content']

admin.site.register(CorfoCodeUser, CorfoCodeUserAdmin)
admin.site.register(CorfoCodeMappingContent, CorfoCodeMappingContentAdmin)
