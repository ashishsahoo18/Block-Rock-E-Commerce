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
from products.models import Product


def home(request):
    products = Product.objects.all().order_by('-created_at')
    featured_products = products[:4]
    deal_product = products.filter(discount__gt=0).order_by('-discount').first()
    if not deal_product:
        deal_product = products.first()

    category_names = list(
        products.exclude(category='')
        .values_list('category', flat=True)
        .distinct()[:9]
    )
    fallback_categories = [
        'Smartphones', 'Laptops', 'Headphones', 'Smartwatches', 'Cameras',
        'Gaming', 'Accessories', 'Audio', 'Drones',
    ]

    return render(request, 'home.html', {
        'featured_products': featured_products,
        'deal_product': deal_product,
        'categories': category_names or fallback_categories,
    })


urlpatterns = [

    path('admin/', admin.site.urls),

    path('', home, name='home'),

    path('accounts/', include('accounts.urls')),

    path('products/', include('products.urls')),

    path('cart/', include('cart.urls')),

    path('orders/', include('orders.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
