from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(is_active=True)

    query = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '').strip()
    min_price_raw = request.GET.get('min_price', '').strip()
    max_price_raw = request.GET.get('max_price', '').strip()
    in_stock_only = request.GET.get('in_stock', '').strip()
    deal_only = request.GET.get('deal', '').strip()
    featured_only = request.GET.get('featured', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    # Search filter
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__name__icontains=query) |
            Q(description__icontains=query)
        )

    # Category filter
    if selected_category:
        products = products.filter(category__slug=selected_category)

    # Price range filters
    min_price = None
    if min_price_raw:
        try:
            min_price = Decimal(min_price_raw)
            products = products.filter(price__gte=min_price)
        except InvalidOperation:
            min_price_raw = ''

    max_price = None
    if max_price_raw:
        try:
            max_price = Decimal(max_price_raw)
            products = products.filter(price__lte=max_price)
        except InvalidOperation:
            max_price_raw = ''

    # Feature & Stock filters
    if in_stock_only in ['1', 'true', 'on']:
        products = products.filter(stock__gt=0)

    if deal_only in ['1', 'true', 'on']:
        products = products.filter(is_deal=True)

    if featured_only in ['1', 'true', 'on']:
        products = products.filter(is_featured=True)

    # Sorting options
    ordering_map = {
        'price_low': ('price', 'name'),
        'price_high': ('-price', 'name'),
        'rating': ('-rating', '-review_count'),
        'name_asc': ('name',),
        'newest': ('-created_at', 'name'),
    }
    products = products.order_by(*ordering_map.get(sort, ('-created_at', 'name')))

    total_results = products.count()

    # Pagination: 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Preserve GET parameters (excluding 'page') for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    filter_querystring = query_params.urlencode()

    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': total_results,
        'categories': categories,
        'query': query,
        'selected_category': selected_category,
        'min_price': min_price_raw,
        'max_price': max_price_raw,
        'in_stock': in_stock_only in ['1', 'true', 'on'],
        'deal': deal_only in ['1', 'true', 'on'],
        'featured': featured_only in ['1', 'true', 'on'],
        'sort': sort,
        'filter_querystring': filter_querystring,
    }

    return render(request, 'products.html', context)


@login_required
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category'), slug=slug, is_active=True,
    )
    return render(request, 'product_detail.html', {'product': product})
