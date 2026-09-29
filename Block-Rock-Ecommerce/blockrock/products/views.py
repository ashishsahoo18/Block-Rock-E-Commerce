from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from products.templatetags.currency_filters import rupee_format

from .models import Category, Product, SizeChart


@login_required
def search_autocomplete(request):
    """Safe, fast search suggestions based on real active products and categories."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    products = (
        Product.objects.filter(is_active=True)
        .filter(Q(name__icontains=q) | Q(category__name__icontains=q) | Q(brand__icontains=q))
        .select_related('category')
        .prefetch_related('images')[:6]
    )

    results = []
    for p in products:
        results.append({
            'name': p.name,
            'slug': p.slug,
            'price': rupee_format(p.current_price),
            'category': p.category.name,
            'collection': p.collection_name,
            'image_url': p.primary_image_url,
        })

    return JsonResponse({'results': results})


@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images', 'variants')
    categories = Category.objects.filter(is_active=True)

    query = request.GET.get('search', '').strip()
    collection = request.GET.get('collection', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_size = request.GET.get('size', '').strip()
    selected_color = request.GET.get('color', '').strip()
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

    # Variant Facet filters (Size & Color)
    if selected_size:
        products = products.filter(variants__size__iexact=selected_size, variants__is_active=True).distinct()

    if selected_color:
        products = products.filter(variants__color_name__iexact=selected_color, variants__is_active=True).distinct()

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

    # Calculate real available facets from the current result set
    matching_product_ids = list(products.values_list('id', flat=True))
    available_sizes = []
    available_colors = []
    from products.models import ProductVariant
    if matching_product_ids:
        raw_sizes = (
            ProductVariant.objects.filter(product_id__in=matching_product_ids, is_active=True)
            .exclude(size='')
            .values_list('size', flat=True)
            .distinct()
        )
        for s in raw_sizes:
            if s and s not in available_sizes:
                available_sizes.append(s)

        raw_colors = (
            ProductVariant.objects.filter(product_id__in=matching_product_ids, is_active=True)
            .exclude(color_name='')
            .values('color_name', 'color_hex')
            .distinct()
        )
        seen_col = set()
        for c in raw_colors:
            if c['color_name'] and c['color_name'] not in seen_col:
                seen_col.add(c['color_name'])
                available_colors.append(c)

    # Sorting options
    ordering_map = {
        'relevance': ('-is_featured', '-is_deal', '-created_at'),
        'price_low': ('price', 'name'),
        'price_high': ('-price', 'name'),
        'discount': ('-discount', '-created_at'),
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

    # Active filters list for chips UI
    active_filters = []
    if selected_category:
        cat_obj = Category.objects.filter(slug=selected_category).first()
        active_filters.append({'type': 'category', 'label': f'Category: {cat_obj.name if cat_obj else selected_category}', 'param': 'category'})
    if selected_size:
        active_filters.append({'type': 'size', 'label': f'Size: {selected_size}', 'param': 'size'})
    if selected_color:
        active_filters.append({'type': 'color', 'label': f'Color: {selected_color}', 'param': 'color'})
    if min_price_raw or max_price_raw:
        p_label = f"Price: ₹{min_price_raw or '0'} - ₹{max_price_raw or '∞'}"
        active_filters.append({'type': 'price', 'label': p_label, 'param': 'price'})
    if deal_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'deal', 'label': 'On Deal', 'param': 'deal'})
    if featured_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'featured', 'label': 'Featured', 'param': 'featured'})
    if in_stock_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'in_stock', 'label': 'In Stock', 'param': 'in_stock'})

    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': total_results,
        'categories': categories,
        'query': query,
        'collection': collection,
        'selected_category': selected_category,
        'selected_size': selected_size,
        'selected_color': selected_color,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
        'active_filters': active_filters,
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
    products = Product.objects.filter(is_active=True, is_ingot_original=True).select_related('category').prefetch_related('images', 'variants')
    categories = Category.objects.filter(is_active=True, is_ingot_original=True)

    query = request.GET.get('search', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_size = request.GET.get('size', '').strip()
    selected_color = request.GET.get('color', '').strip()
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

    if selected_size:
        products = products.filter(variants__size__iexact=selected_size, variants__is_active=True).distinct()

    if selected_color:
        products = products.filter(variants__color_name__iexact=selected_color, variants__is_active=True).distinct()

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

    matching_product_ids = list(products.values_list('id', flat=True))
    available_sizes = []
    available_colors = []
    from products.models import ProductVariant
    if matching_product_ids:
        raw_sizes = (
            ProductVariant.objects.filter(product_id__in=matching_product_ids, is_active=True)
            .exclude(size='')
            .values_list('size', flat=True)
            .distinct()
        )
        for s in raw_sizes:
            if s and s not in available_sizes:
                available_sizes.append(s)

        raw_colors = (
            ProductVariant.objects.filter(product_id__in=matching_product_ids, is_active=True)
            .exclude(color_name='')
            .values('color_name', 'color_hex')
            .distinct()
        )
        seen_col = set()
        for c in raw_colors:
            if c['color_name'] and c['color_name'] not in seen_col:
                seen_col.add(c['color_name'])
                available_colors.append(c)

    ordering_map = {
        'relevance': ('-is_featured', '-is_deal', '-created_at'),
        'price_low': ('price', 'name'),
        'price_high': ('-price', 'name'),
        'discount': ('-discount', '-created_at'),
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

    active_filters = []
    if selected_category:
        cat_obj = Category.objects.filter(slug=selected_category).first()
        active_filters.append({'type': 'category', 'label': f'Category: {cat_obj.name if cat_obj else selected_category}', 'param': 'category'})
    if selected_size:
        active_filters.append({'type': 'size', 'label': f'Size: {selected_size}', 'param': 'size'})
    if selected_color:
        active_filters.append({'type': 'color', 'label': f'Color: {selected_color}', 'param': 'color'})
    if min_price_raw or max_price_raw:
        p_label = f"Price: ₹{min_price_raw or '0'} - ₹{max_price_raw or '∞'}"
        active_filters.append({'type': 'price', 'label': p_label, 'param': 'price'})
    if deal_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'deal', 'label': 'On Deal', 'param': 'deal'})
    if featured_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'featured', 'label': 'Featured', 'param': 'featured'})
    if in_stock_only in ['1', 'true', 'on']:
        active_filters.append({'type': 'in_stock', 'label': 'In Stock', 'param': 'in_stock'})

    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'total_results': total_results,
        'categories': categories,
        'query': query,
        'collection': 'ingot_originals',
        'selected_category': selected_category,
        'selected_size': selected_size,
        'selected_color': selected_color,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
        'active_filters': active_filters,
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
        Product.objects.select_related('category').prefetch_related('images', 'variants'),
        slug=slug,
        is_active=True,
    )
    # Admin-editable size chart lookup
    size_chart = (
        SizeChart.objects.filter(is_active=True, category=product.category).first()
        or SizeChart.objects.filter(is_active=True).first()
    )

    # Related products from same category or collection
    related_products = list(
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .select_related('category')
        .prefetch_related('images')[:4]
    )
    if len(related_products) < 4:
        extra = list(
            Product.objects.filter(is_active=True, is_ingot_original=product.is_ingot_original)
            .exclude(pk=product.pk)
            .exclude(pk__in=[p.pk for p in related_products])
            .select_related('category')
            .prefetch_related('images')[:4 - len(related_products)]
        )
        related_products.extend(extra)

    # All images sorted
    gallery_images = list(product.images.all().order_by('sort_order', 'id'))

    return render(request, 'product_detail.html', {
        'product': product,
        'gallery_images': gallery_images,
        'size_chart': size_chart,
        'related_products': related_products,
    })
