from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(is_active=True)
    query = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(brand__icontains=query))
    if selected_category:
        products = products.filter(category__slug=selected_category)

    ordering = {
        'price_low': 'price',
        'price_high': '-price',
        'rating': '-rating',
        'newest': '-created_at',
    }
    products = products.order_by(ordering.get(sort, '-created_at'))

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': selected_category,
        'sort': sort,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category'), slug=slug, is_active=True,
    )
    return render(request, 'product_detail.html', {'product': product})
