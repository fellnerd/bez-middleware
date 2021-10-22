from django.urls import path
from dispo_controller import views

urlpatterns = [
    #path('create_credit_proforma', views.create_credit_proforma),
    path('create_credit', views.create_credit),
    path('create_contract', views.create_contract),
    path('create_claim', views.create_claim),
    path('test', views.make_test),
    path('helpers/create_supplier_amount_ref', views.create_supplier_amount_ref),
    path('make_order', views.make_order)
]