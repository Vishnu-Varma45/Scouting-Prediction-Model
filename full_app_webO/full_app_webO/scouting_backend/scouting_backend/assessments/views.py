from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Assessment, TestResult
from .serializers import (
    AssessmentSerializer, AssessmentListSerializer, TestResultSerializer
)
from analysis.runner import (
    run_sprint, run_jump, run_shuttle, run_cone, run_footwork,
    compute_overall_score
)


class AssessmentListCreateView(generics.ListCreateAPIView):
    """GET  /api/assessments/  — list all assessments by this scout.
       POST /api/assessments/  — create a new assessment session."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AssessmentListSerializer
        return AssessmentSerializer

    def get_queryset(self):
        qs = Assessment.objects.filter(scout=self.request.user).select_related('player')
        player_id = self.request.query_params.get('player')
        if player_id:
            qs = qs.filter(player_id=player_id)
        return qs


class AssessmentDetailView(generics.RetrieveUpdateAPIView):
    """GET   /api/assessments/{id}/ — full assessment with all test results.
       PATCH /api/assessments/{id}/ — update notes / status."""
    serializer_class   = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Assessment.objects.filter(scout=self.request.user)


class UploadAndAnalyzeView(APIView):
    """
    POST /api/assessments/{assessment_id}/tests/{test_type}/upload/

    Accepts a video file (or JSON for cone test), runs the AI pipeline,
    saves metrics, and returns the result.

    test_type must be one of: sprint | jump | shuttle | cone | footwork
    """
    permission_classes = [permissions.IsAuthenticated]

    VALID_TESTS = ['sprint', 'jump', 'shuttle', 'cone', 'footwork']

    def post(self, request, assessment_id, test_type):
        print(f"\n>>> UPLOAD VIEW HIT: assessment={assessment_id} test={test_type}")
        print(f">>> REQUEST DATA KEYS: {list(request.data.keys())}")
        print(f">>> CONTENT TYPE: {request.content_type}")
        if test_type not in self.VALID_TESTS:
            return Response(
                {"error": f"Unknown test type '{test_type}'. Must be one of: {self.VALID_TESTS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assessment = get_object_or_404(
            Assessment, pk=assessment_id, scout=request.user
        )

        # Get or create the TestResult record for this test
        test_result, created = TestResult.objects.get_or_create(
            assessment=assessment,
            test_type=test_type,
            defaults={"status": "pending"}
        )

        # Mark as processing
        test_result.status = 'processing'
        test_result.save(update_fields=['status'])

        # ── Cone test: receives JSON directly (live camera test) ───────────────
        # Cone test — accepts either JSON metrics payload or uploaded JSON file
        if test_type == 'cone':
            # Check if a JSON file was uploaded
            json_file = request.FILES.get('json_file')
            if json_file:
                import json
                raw = json.loads(json_file.read())
                # Handle both full export format and raw summary
                payload = raw.get('summary', raw)
            else:
                payload = request.data.get('metrics')

            if not payload:
                test_result.status = 'failed'
                test_result.error  = 'No metrics payload or JSON file provided'
                test_result.save()
                return Response({"error": test_result.error}, status=status.HTTP_400_BAD_REQUEST)

            result = run_cone(payload)

        # ── Video-based tests ──────────────────────────────────────────────────
        else:
            video_file = request.FILES.get('video')
            if not video_file:
                test_result.status = 'failed'
                test_result.error  = 'No video file provided'
                test_result.save()
                return Response({"error": test_result.error}, status=status.HTTP_400_BAD_REQUEST)

            # Save the video
            test_result.video = video_file
            test_result.save(update_fields=['video'])

            video_path = test_result.video.path

            # Run the correct AI pipeline
            if test_type == 'sprint':
                result = run_sprint(video_path)
            elif test_type == 'jump':
                result = run_jump(video_path)
            elif test_type == 'shuttle':
                result = run_shuttle(video_path)
            elif test_type == 'footwork':
                calibration = request.data.get('calibration_points')
                result = run_footwork(video_path, calibration)

        # ── Save results ───────────────────────────────────────────────────────
        if 'error' in result and result['error']:
            test_result.status  = 'failed'
            test_result.error   = result['error']
            test_result.metrics = result.get('metrics', {})
            test_result.score   = 0
        else:
            test_result.status  = 'completed'
            test_result.metrics = result['metrics']
            test_result.score   = result['score']
            test_result.error   = ''

        test_result.save()

        # Recompute overall assessment score
        all_results = assessment.test_results.all()
        assessment.overall_score = compute_overall_score(all_results)

        # Auto-mark as completed when all 5 tests are done
        completed_count = all_results.filter(status='completed').count()
        if completed_count == 5:
            assessment.status = 'completed'

        assessment.save(update_fields=['overall_score', 'status'])

        serializer = TestResultSerializer(test_result)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TestResultDetailView(generics.RetrieveAPIView):
    """GET /api/tests/{id}/ — get a single test result with full metrics."""
    serializer_class   = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TestResult.objects.filter(assessment__scout=self.request.user)


class AssessmentScoreView(APIView):
    """GET /api/assessments/{id}/score/ — get the overall score summary."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, assessment_id):
        assessment = get_object_or_404(
            Assessment, pk=assessment_id, scout=request.user
        )
        results = assessment.test_results.all()

        breakdown = {}
        for tr in results:
            breakdown[tr.test_type] = {
                "status": tr.status,
                "score" : tr.score,
            }

        return Response({
            "assessment_id"  : assessment.pk,
            "player"         : assessment.player.full_name,
            "overall_score"  : assessment.overall_score,
            "recommendation" : assessment.recommendation,
            "status"         : assessment.status,
            "test_breakdown" : breakdown,
        })
