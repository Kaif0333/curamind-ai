from rest_framework import serializers


class AIResultSerializer(serializers.Serializer):
    anomaly_probability = serializers.FloatField()
    heatmap = serializers.CharField(allow_blank=True)
    model = serializers.CharField()


class AIProcessingLogSerializer(serializers.Serializer):
    _id = serializers.CharField()
    image_id = serializers.CharField()
    stage = serializers.CharField()
    status = serializers.CharField()
    details = serializers.JSONField()
