from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Cart, CartItem, Wishlist, WishlistItem


@transaction.atomic
def add_product_to_cart(user, product, quantity=1):
    if not product.is_active:
        raise ValidationError('This product is no longer available.')
    if product.stock < 1:
        raise ValidationError('This product is currently out of stock.')
    if quantity < 1:
        raise ValidationError('Quantity must be at least one.')

    cart, _ = Cart.objects.get_or_create(user=user)
    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart, product=product, defaults={'quantity': 0},
    )
    desired_quantity = item.quantity + quantity
    if desired_quantity > product.stock:
        raise ValidationError(f'Only {product.stock} units are available.')
    item.quantity = desired_quantity
    item.save(update_fields=['quantity', 'updated_at'])
    return item, created


@transaction.atomic
def add_product_to_wishlist(user, product):
    if not product.is_active:
        raise ValidationError('This product is no longer available.')
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
