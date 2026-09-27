from products.models import Category
from .models import Cart, Wishlist


def cart_and_wishlist(request):
    nav_categories = Category.objects.filter(is_active=True).order_by('name')
    originals_categories = Category.objects.filter(is_active=True, is_ingot_original=True).order_by('name')
    marketplace_categories = Category.objects.filter(is_active=True, is_ingot_original=False).order_by('name')

    base_context = {
        'nav_categories': nav_categories,
        'originals_categories': originals_categories,
        'marketplace_categories': marketplace_categories,
    }

    if not request.user.is_authenticated:
        base_context.update({'cart_count': 0, 'wishlist_product_ids': set()})
        return base_context

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

    base_context.update({'cart_count': cart_count, 'wishlist_product_ids': wishlist_product_ids})
    return base_context
