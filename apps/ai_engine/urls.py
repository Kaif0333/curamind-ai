from django.urls import path

from apps.ai_engine.views import AIProcessingLogsView, AIResultView

urlpatterns = [
    path("logs", AIProcessingLogsView.as_view(), name="ai-logs"),
    path("result", AIResultView.as_view(), name="ai-result"),
]
