from django.urls import path

from . import views


urlpatterns = [


    path('', views.products, name="products"),


    path('<int:id>/', views.product_detail, name="product_detail"),


]