"""
URL configuration for blockrock project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static
from products.models import Category, Product


def home(request):
    featured_products = (
        Product.objects.filter(is_featured=True, is_active=True)
        .select_related('category')[:4]
    )
    deal_product = (
        Product.objects.filter(is_deal=True, is_active=True)
        .select_related('category').first()
    )
    categories = Category.objects.filter(is_active=True)[:9]

    return render(request, 'home.html', {
        'featured_products': featured_products,
        'deal_product': deal_product,
        'categories': categories,
    })


urlpatterns = [

    path('admin/', admin.site.urls),

    path('', include('accounts.urls')),

    path('', home, name='home'),

    path('shop/', include('products.urls')),

    path('products/', include('products.urls')),

    path('cart/', include('cart.urls')),

    path('wishlist/', include('cart.wishlist_urls')),

    path('orders/', include('orders.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
