from django.urls import path

from apps.imaging.views import ImageUploadView

urlpatterns = [
    path("upload", ImageUploadView.as_view(), name="image-upload"),
]
