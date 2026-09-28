from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from products.models import Product

from .models import Cart, CartItem, Wishlist, WishlistItem
from .services import add_product_to_cart, add_product_to_wishlist


def _return_url(request, fallback):
    candidate = request.POST.get('next')
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}):
        return candidate
    return fallback


def _cart_for_user(user):
    return Cart.objects.get_or_create(user=user)[0]


from django.http import HttpResponseNotAllowed, JsonResponse

@login_required
def cart_detail(request):
    cart = _cart_for_user(request.user)
    items = cart.items.select_related('product', 'variant', 'product__category').filter(product__is_active=True)
    total = sum((item.subtotal for item in items), Decimal('0.00'))
    return render(request, 'cart/cart.html', {'cart': cart, 'items': items, 'total': total})


@login_required
@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '')
    )
    is_buy_now = request.POST.get('action') == 'buy_now'
    variant_id = request.POST.get('variant_id') or None
    size = request.POST.get('size') or None
    color = request.POST.get('color') or None

    try:
        quantity = int(request.POST.get('quantity', 1))
        item, created = add_product_to_cart(
            user=request.user,
            product=product,
            quantity=quantity,
            variant_id=variant_id,
            size=size,
            color=color,
        )
        variant_desc = f" ({item.variant_label})" if item.variant_label else ""
        message = (
            f'{product.name}{variant_desc} added to your cart.'
            if created
            else f'Updated {product.name}{variant_desc} quantity to {item.quantity}.'
        )
        messages.success(request, message)

        if is_buy_now:
            return redirect('checkout')

        if is_ajax:
            cart = _cart_for_user(request.user)
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_count': cart.item_count,
            })

    except (ValueError, ValidationError) as error:
        err_msg = error.messages[0] if hasattr(error, 'messages') else str(error)
        messages.error(request, err_msg)
        if is_ajax:
            return JsonResponse({'success': False, 'error': err_msg}, status=400)

    return redirect(_return_url(request, reverse('cart_detail')))


@login_required
@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(
        CartItem.objects.select_related('product', 'variant'),
        pk=item_id,
        cart__user=request.user
    )
    action = request.POST.get('action')
    try:
        if action == 'increase':
            quantity = item.quantity + 1
        elif action == 'decrease':
            quantity = item.quantity - 1
        else:
            quantity = int(request.POST.get('quantity', item.quantity))
        if quantity < 1:
            raise ValidationError('Quantity must be at least one. Use remove to delete an item.')
        max_allowed = item.available_stock
        if quantity > max_allowed:
            raise ValidationError(f'Only {max_allowed} units are available.')
        item.quantity = quantity
        item.save(update_fields=['quantity', 'updated_at'])
        messages.success(request, f'Updated {item.product.name} quantity.')
    except (ValueError, ValidationError) as error:
        messages.error(request, error.messages[0] if hasattr(error, 'messages') else 'Enter a valid quantity.')
    return redirect('cart_detail')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    name = item.product.name
    item.delete()
    messages.success(request, f'{name} removed from your cart.')
    return redirect('cart_detail')


@login_required
def wishlist_detail(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    items = wishlist.items.select_related('product', 'product__category').filter(product__is_active=True)
    return render(request, 'wishlist/wishlist.html', {'wishlist': wishlist, 'items': items})


@login_required
@require_POST
def add_to_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    try:
        _, created = add_product_to_wishlist(request.user, product)
        if created:
            messages.success(request, f'{product.name} added to your wishlist.')
        else:
            messages.info(request, f'{product.name} is already in your wishlist.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect(_return_url(request, reverse('wishlist_detail')))


@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, wishlist__user=request.user)
    name = item.product.name
    item.delete()
    messages.success(request, f'{name} removed from your wishlist.')
    return redirect('wishlist_detail')


@login_required
@require_POST
def move_wishlist_to_cart(request, item_id):
    item = get_object_or_404(WishlistItem.objects.select_related('product'), pk=item_id, wishlist__user=request.user)
    try:
        add_product_to_cart(request.user, item.product)
        messages.success(request, f'{item.product.name} added to your cart. It remains in your wishlist.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect('wishlist_detail')


@login_required
@require_POST
def toggle_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    item = wishlist.items.filter(product=product).first()
    if item:
        item.delete()
        in_wishlist = False
        message = f'{product.name} removed from your wishlist.'
    else:
        wishlist.items.create(product=product)
        in_wishlist = True
        message = f'{product.name} added to your wishlist.'

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    if is_ajax:
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': message,
            'wishlist_count': wishlist.items.count()
        })
    messages.success(request, message)
    return redirect(_return_url(request, reverse('wishlist_detail')))
