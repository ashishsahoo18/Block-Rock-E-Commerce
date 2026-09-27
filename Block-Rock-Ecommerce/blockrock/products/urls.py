from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='products'),
    path('api/search-autocomplete/', views.search_autocomplete, name='search_autocomplete'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
]
