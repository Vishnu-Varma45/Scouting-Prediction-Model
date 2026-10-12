from django.contrib import admin
from .models import Assessment, TestResult

class TestResultInline(admin.TabularInline):
    model  = TestResult
    extra  = 0
    fields = ['test_type', 'status', 'score', 'created_at']
    readonly_fields = ['created_at']

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display   = ['id', 'player', 'scout', 'status', 'overall_score', 'recommendation', 'created_at']
    list_filter    = ['status', 'recommendation']
    search_fields  = ['player__full_name', 'scout__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines        = [TestResultInline]

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display  = ['id', 'assessment', 'test_type', 'status', 'score', 'created_at']
    list_filter   = ['test_type', 'status']
    readonly_fields = ['created_at', 'updated_at', 'metrics']
