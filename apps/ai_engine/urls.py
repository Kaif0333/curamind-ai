from django.urls import path

from apps.ai_engine.views import AIResultView

urlpatterns = [
    path("result", AIResultView.as_view(), name="ai-result"),
]
