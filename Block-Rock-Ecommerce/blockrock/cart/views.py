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


@login_required
def cart_detail(request):
    cart = _cart_for_user(request.user)
    items = cart.items.select_related('product').filter(product__is_active=True)
    total = sum((item.subtotal for item in items), Decimal('0.00'))
    return render(request, 'cart/cart.html', {'cart': cart, 'items': items, 'total': total})


@login_required
@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
        item, created = add_product_to_cart(request.user, product, quantity)
        message = f'{product.name} added to your cart.' if created else f'Updated {product.name} quantity to {item.quantity}.'
        messages.success(request, message)
    except (ValueError, ValidationError) as error:
        messages.error(request, error.messages[0] if hasattr(error, 'messages') else 'Enter a valid quantity.')
    return redirect(_return_url(request, reverse('cart_detail')))


@login_required
@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem.objects.select_related('product'), pk=item_id, cart__user=request.user)
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
        if quantity > item.product.stock:
            raise ValidationError(f'Only {item.product.stock} units are available.')
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
