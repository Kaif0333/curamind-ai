from django.http import HttpResponse

def home(request):
    return HttpResponse("CuraMind AI Backend is running 🚀")
