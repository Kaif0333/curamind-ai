from rest_framework import serializers


class AIResultSerializer(serializers.Serializer):
    anomaly_probability = serializers.FloatField()
    heatmap = serializers.CharField(allow_blank=True)
    model = serializers.CharField()
    model_version = serializers.CharField(required=False, allow_blank=True)
    device = serializers.CharField(required=False, allow_blank=True)


class AIProcessingLogSerializer(serializers.Serializer):
    _id = serializers.CharField()
    image_id = serializers.CharField()
    stage = serializers.CharField()
    status = serializers.CharField()
    details = serializers.JSONField()
