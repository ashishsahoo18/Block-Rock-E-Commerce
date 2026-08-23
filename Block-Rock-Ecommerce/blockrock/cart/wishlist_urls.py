from django.urls import path

from . import views

urlpatterns = [
    path('', views.wishlist_detail, name='wishlist_detail'),
    path('add/<slug:slug>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('move-to-cart/<int:item_id>/', views.move_wishlist_to_cart, name='move_wishlist_to_cart'),
]
