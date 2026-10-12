from rest_framework import serializers
from .models import Player


class PlayerSerializer(serializers.ModelSerializer):
    registered_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Player
        fields = [
            'id', 'full_name', 'age', 'gender', 'dominant_foot',
            'height_cm', 'weight_kg',
            'village', 'district', 'state',
            'experience_level',
            'registered_by', 'registered_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'registered_by', 'created_at', 'updated_at']

    def get_registered_by_name(self, obj):
        if obj.registered_by:
            return obj.registered_by.get_full_name() or obj.registered_by.username
        return None

    def create(self, validated_data):
        # Automatically set the scout from the request user
        validated_data['registered_by'] = self.context['request'].user
        return super().create(validated_data)
