from rest_framework import serializers


class AIResultSerializer(serializers.Serializer):
    anomaly_probability = serializers.FloatField()
    anomaly_threshold = serializers.FloatField(required=False)
    is_anomalous = serializers.BooleanField(required=False)
    heatmap = serializers.CharField(allow_blank=True)
    model = serializers.CharField()
    model_version = serializers.CharField(required=False, allow_blank=True)
    device = serializers.CharField(required=False, allow_blank=True)
    model_registry = serializers.CharField(required=False, allow_blank=True)
    weights_sha256 = serializers.CharField(required=False, allow_blank=True)
    input_sha256 = serializers.CharField(required=False, allow_blank=True)
    image_id = serializers.CharField(required=False, allow_blank=True)
    service_processing_ms = serializers.FloatField(required=False)


class AIProcessingLogSerializer(serializers.Serializer):
    _id = serializers.CharField()
    image_id = serializers.CharField()
    stage = serializers.CharField()
    status = serializers.CharField()
    details = serializers.JSONField()
