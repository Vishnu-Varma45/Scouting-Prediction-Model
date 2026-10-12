from django.urls import path
from .views import (
    AssessmentListCreateView,
    AssessmentDetailView,
    UploadAndAnalyzeView,
    TestResultDetailView,
    AssessmentScoreView,
)

urlpatterns = [
    path('',
         AssessmentListCreateView.as_view(),
         name='assessment-list-create'),

    path('<int:pk>/',
         AssessmentDetailView.as_view(),
         name='assessment-detail'),

    path('<int:assessment_id>/score/',
         AssessmentScoreView.as_view(),
         name='assessment-score'),

    path('<int:assessment_id>/tests/<str:test_type>/upload/',
         UploadAndAnalyzeView.as_view(),
         name='test-upload-analyze'),
]
