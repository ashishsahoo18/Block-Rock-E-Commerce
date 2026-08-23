from .models import Cart, Wishlist


def cart_and_wishlist(request):
    if not request.user.is_authenticated:
        return {'cart_count': 0, 'wishlist_product_ids': set()}

    cart_count = 0
    wishlist_product_ids = set()
    try:
        cart_count = sum(item.quantity for item in Cart.objects.get(user=request.user).items.all())
    except Cart.DoesNotExist:
        pass
    try:
        wishlist_product_ids = set(Wishlist.objects.get(user=request.user).items.values_list('product_id', flat=True))
    except Wishlist.DoesNotExist:
        pass
    return {'cart_count': cart_count, 'wishlist_product_ids': wishlist_product_ids}
