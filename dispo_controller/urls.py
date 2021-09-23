from django.urls import path
from dispo_controller import views

urlpatterns = [
    path('test/', views.test),
]