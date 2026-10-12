from django.contrib import admin
from .models import Player

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'age', 'gender', 'village', 'district', 'registered_by', 'created_at']
    search_fields = ['full_name', 'village', 'district']
    list_filter   = ['gender', 'experience_level', 'district']
    readonly_fields = ['created_at', 'updated_at']
