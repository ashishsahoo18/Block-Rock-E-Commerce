from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from accounts.models import Subscriber
from products.models import Category, Product
from products import views as product_views


@login_required
def home(request):
    featured_electronics = (
        Product.objects.filter(is_featured=True, is_ingot_original=False, is_active=True)
        .select_related('category')[:4]
    )
    ingot_originals_featured = (
        Product.objects.filter(is_ingot_original=True, is_active=True)
        .select_related('category')[:4]
    )
    deals_of_the_day = (
        Product.objects.filter(is_deal=True, is_active=True)
        .select_related('category')[:4]
    )
    deal_product = (
        Product.objects.filter(is_deal=True, is_active=True)
        .select_related('category').first()
    )
    trending_products = (
        Product.objects.filter(is_active=True)
        .order_by('-rating', '-created_at')
        .select_related('category')[:4]
    )
    categories = Category.objects.filter(is_active=True)
    active_subscriber_count = Subscriber.objects.filter(is_active=True).count()

    return render(request, 'home.html', {
        'featured_electronics': featured_electronics,
        'featured_products': featured_electronics,  # backwards compatibility with existing templates
        'ingot_originals_featured': ingot_originals_featured,
        'deals_of_the_day': deals_of_the_day,
        'deal_product': deal_product,
        'trending_products': trending_products,
        'categories': categories,
        'active_subscriber_count': active_subscriber_count,
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', home, name='home'),
    path('shop/', include('products.urls')),
    path('products/', include('products.urls')),
    path('ingot-originals/', product_views.ingot_originals, name='ingot_originals'),
    path('cart/', include('cart.urls')),
    path('wishlist/', include('cart.wishlist_urls')),
    path('orders/', include('orders.urls')),
    path('checkout/', include('orders.checkout_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
