from django.contrib import admin
from .models import CorfoCodeUser, CorfoCodeMappingContent

# Register your models here.


class CorfoCodeUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'mapping_content', 'code','created_at')
    search_fields = ['user__username', 'mapping_content__id_content','mapping_content__content', 'code', 'created_at']
    ordering = ['-created_at']

class CorfoCodeMappingContentAdmin(admin.ModelAdmin):
    list_display = ('id_content', 'content')
    search_fields = ['id_content', 'content']
    ordering = ['-id_content']

admin.site.register(CorfoCodeUser, CorfoCodeUserAdmin)
admin.site.register(CorfoCodeMappingContent, CorfoCodeMappingContentAdmin)
