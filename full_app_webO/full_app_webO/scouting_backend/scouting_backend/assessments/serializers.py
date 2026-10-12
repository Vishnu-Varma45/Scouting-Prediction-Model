from rest_framework import serializers
from .models import Assessment, TestResult
from players.serializers import PlayerSerializer


class TestResultSerializer(serializers.ModelSerializer):
    test_type_display = serializers.CharField(source='get_test_type_display', read_only=True)

    class Meta:
        model  = TestResult
        fields = [
            'id', 'assessment', 'test_type', 'test_type_display',
            'status', 'video', 'metrics', 'score', 'error',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'metrics', 'score', 'error', 'created_at', 'updated_at']


class TestResultUploadSerializer(serializers.ModelSerializer):
    """Used only for video upload — accepts a video file."""
    class Meta:
        model  = TestResult
        fields = ['id', 'video']


class AssessmentSerializer(serializers.ModelSerializer):
    test_results    = TestResultSerializer(many=True, read_only=True)
    player_detail   = PlayerSerializer(source='player', read_only=True)
    scout_name      = serializers.SerializerMethodField()
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Assessment
        fields = [
            'id', 'player', 'player_detail',
            'scout', 'scout_name',
            'status', 'status_display',
            'scout_notes', 'overall_score', 'recommendation',
            'test_results',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'scout', 'overall_score', 'created_at', 'updated_at']

    def get_scout_name(self, obj):
        if obj.scout:
            return obj.scout.get_full_name() or obj.scout.username
        return None

    def create(self, validated_data):
        validated_data['scout'] = self.context['request'].user
        return super().create(validated_data)


class AssessmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested test results."""
    player_name    = serializers.CharField(source='player.full_name', read_only=True)
    player_village = serializers.CharField(source='player.village',    read_only=True)
    scout_name     = serializers.SerializerMethodField()
    tests_done     = serializers.SerializerMethodField()

    class Meta:
        model  = Assessment
        fields = [
            'id', 'player', 'player_name', 'player_village',
            'scout_name', 'status', 'overall_score', 'recommendation',
            'tests_done', 'created_at',
        ]

    def get_scout_name(self, obj):
        if obj.scout:
            return obj.scout.get_full_name() or obj.scout.username
        return None

    def get_tests_done(self, obj):
        return obj.test_results.filter(status='completed').count()
