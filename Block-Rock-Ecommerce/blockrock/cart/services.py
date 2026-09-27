from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Cart, CartItem, Wishlist, WishlistItem


@transaction.atomic
def add_product_to_cart(user, product, quantity=1, variant_id=None, size=None, color=None):
    if not product.is_active:
        raise ValidationError('This product is no longer available.')
    if quantity < 1:
        raise ValidationError('Quantity must be at least one.')

    # Check if product requires variant selection
    active_variants = product.variants.filter(is_active=True)
    selected_variant = None

    if active_variants.exists():
        if variant_id:
            try:
                selected_variant = active_variants.get(pk=variant_id)
            except active_variants.model.DoesNotExist:
                raise ValidationError('Selected product variant is invalid.')
        elif size or color:
            query = active_variants
            if size:
                query = query.filter(size__iexact=size.strip())
            if color:
                query = query.filter(color_name__iexact=color.strip())
            selected_variant = query.first()
            if not selected_variant:
                raise ValidationError('Selected size or color combination is unavailable.')
        else:
            # Variants exist on product but none selected
            raise ValidationError('Please select a size and color before adding to cart.')

    if selected_variant:
        if selected_variant.stock < 1:
            raise ValidationError(f'"{product.name} ({selected_variant.display_name})" is currently out of stock.')
    else:
        if product.stock < 1:
            raise ValidationError(f'"{product.name}" is currently out of stock.')

    cart, _ = Cart.objects.get_or_create(user=user)
    variant_label = selected_variant.display_name if selected_variant else ''

    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart,
        product=product,
        variant=selected_variant,
        defaults={'quantity': 0, 'variant_label': variant_label},
    )

    max_stock = selected_variant.stock if selected_variant else product.stock
    desired_quantity = item.quantity + quantity
    if desired_quantity > max_stock:
        raise ValidationError(f'Only {max_stock} units are available.')

    item.quantity = desired_quantity
    if variant_label and not item.variant_label:
        item.variant_label = variant_label
    item.save(update_fields=['quantity', 'variant_label', 'updated_at'])
    return item, created


@transaction.atomic
def add_product_to_wishlist(user, product):
    if not product.is_active:
        raise ValidationError('This product is no longer available.')
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
