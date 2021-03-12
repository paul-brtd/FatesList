from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse


def index(request):
    return HttpResponse("You likely want https://dev.fateslist.xyz instead :)")
