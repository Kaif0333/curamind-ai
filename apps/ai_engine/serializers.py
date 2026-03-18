from rest_framework import serializers


class AIResultSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    result = serializers.JSONField()
