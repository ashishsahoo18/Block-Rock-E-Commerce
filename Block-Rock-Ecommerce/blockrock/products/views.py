from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from products.templatetags.currency_filters import rupee_format

from .models import Category, Product


@login_required
def search_autocomplete(request):
    """Safe, fast search suggestions based on real active products and categories."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    products = (
        Product.objects.filter(is_active=True)
        .filter(Q(name__icontains=q) | Q(category__name__icontains=q) | Q(brand__icontains=q))
        .select_related('category')[:6]
    )

    results = []
    for p in products:
        results.append({
            'name': p.name,
            'slug': p.slug,
            'price': rupee_format(p.current_price),
            'category': p.category.name,
            'collection': p.collection_name,
            'image_url': p.image.url if p.image else '',
        })

    return JsonResponse({'results': results})


@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(is_active=True)

    query = request.GET.get('search', '').strip()
    collection = request.GET.get('collection', '').strip()
    selected_category = request.GET.get('category', '').strip()
    min_price_raw = request.GET.get('min_price', '').strip()
    max_price_raw = request.GET.get('max_price', '').strip()
    in_stock_only = request.GET.get('in_stock', '').strip()
    deal_only = request.GET.get('deal', '').strip()
    featured_only = request.GET.get('featured', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    # Collection filter
    if collection == 'electronics':
        products = products.filter(is_ingot_original=False)
        categories = categories.filter(is_ingot_original=False)
    elif collection == 'ingot_originals':
        products = products.filter(is_ingot_original=True)
        categories = categories.filter(is_ingot_original=True)

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
        'relevance': ('-is_featured', '-is_deal', '-created_at'),
        'price_low': ('price', 'name'),
        'price_high': ('-price', 'name'),
        'rating': ('-rating', '-review_count'),
        'name_asc': ('name',),
        'newest': ('-created_at', 'name'),
    }
    products = products.order_by(*ordering_map.get(sort, ('-created_at', 'name')))

    total_results = products.count()
    electronics_count = Product.objects.filter(is_active=True, is_ingot_original=False).count()
    originals_count = Product.objects.filter(is_active=True, is_ingot_original=True).count()

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
        'collection': collection,
        'selected_category': selected_category,
        'min_price': min_price_raw,
        'max_price': max_price_raw,
        'in_stock': in_stock_only in ['1', 'true', 'on'],
        'deal': deal_only in ['1', 'true', 'on'],
        'featured': featured_only in ['1', 'true', 'on'],
        'sort': sort,
        'filter_querystring': filter_querystring,
        'electronics_count': electronics_count,
        'originals_count': originals_count,
    }

    return render(request, 'products.html', context)


@login_required
def ingot_originals(request):
    """Dedicated collection page for INGOT Originals lifestyle collection."""
    products = Product.objects.filter(is_active=True, is_ingot_original=True).select_related('category')
    categories = Category.objects.filter(is_active=True, is_ingot_original=True)

    query = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '').strip()
    min_price_raw = request.GET.get('min_price', '').strip()
    max_price_raw = request.GET.get('max_price', '').strip()
    in_stock_only = request.GET.get('in_stock', '').strip()
    deal_only = request.GET.get('deal', '').strip()
    featured_only = request.GET.get('featured', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(description__icontains=query)
        )

    if selected_category:
        products = products.filter(category__slug=selected_category)

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

    if in_stock_only in ['1', 'true', 'on']:
        products = products.filter(stock__gt=0)
    if deal_only in ['1', 'true', 'on']:
        products = products.filter(is_deal=True)
    if featured_only in ['1', 'true', 'on']:
        products = products.filter(is_featured=True)

    ordering_map = {
        'relevance': ('-is_featured', '-is_deal', '-created_at'),
        'price_low': ('price', 'name'),
        'price_high': ('-price', 'name'),
        'rating': ('-rating', '-review_count'),
        'name_asc': ('name',),
        'newest': ('-created_at', 'name'),
    }
    products = products.order_by(*ordering_map.get(sort, ('-created_at', 'name')))
    total_results = products.count()

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

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
        'collection': 'ingot_originals',
        'selected_category': selected_category,
        'min_price': min_price_raw,
        'max_price': max_price_raw,
        'in_stock': in_stock_only in ['1', 'true', 'on'],
        'deal': deal_only in ['1', 'true', 'on'],
        'featured': featured_only in ['1', 'true', 'on'],
        'sort': sort,
        'filter_querystring': filter_querystring,
    }
    return render(request, 'ingot_originals.html', context)


@login_required
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category'), slug=slug, is_active=True,
    )
    # Related products from same category or collection
    related_products = list(
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .select_related('category')[:4]
    )
    if len(related_products) < 4:
        extra = list(
            Product.objects.filter(is_active=True, is_ingot_original=product.is_ingot_original)
            .exclude(pk=product.pk)
            .exclude(pk__in=[p.pk for p in related_products])
            .select_related('category')[:4 - len(related_products)]
        )
        related_products.extend(extra)

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
    })
