from django.shortcuts import render
from django.http import JsonResponse


def home(request):
    return render(request, "home.html")


def docs(request):
    return render(request, "api_docs.html")


def routes(request):
    return render(request, "docs.html")


def health(request):
    return JsonResponse({"status": "ok"})
