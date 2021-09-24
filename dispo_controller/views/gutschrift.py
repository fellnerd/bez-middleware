from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status


# Create your views here.
@api_view(['GET', 'POST'])
def test(request):
    return Response("OK")


# Gutschrift erstellen
@api_view(['GET', 'POST'])
def create_credit(request):
    
    return Response("OK")