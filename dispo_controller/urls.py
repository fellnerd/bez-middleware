from django.urls import path
from dispo_controller import views

urlpatterns = [
    path('create_credit/', views.create_credit),
]