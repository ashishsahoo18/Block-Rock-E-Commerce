from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<str:order_number>/', views.order_detail, name='order_detail'),
    path('<str:order_number>/confirmation/', views.order_confirmation, name='order_confirmation'),
]