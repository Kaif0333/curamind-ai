from django.urls import path

from apps.imaging.views import ImageDownloadView, ImageUploadView

urlpatterns = [
    path("<uuid:image_id>/download", ImageDownloadView.as_view(), name="image-download"),
    path("upload", ImageUploadView.as_view(), name="image-upload"),
]
