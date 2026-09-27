from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.select_related('product')), Decimal('0.00'))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f'{self.user.username} cart'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    variant_label = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['cart', 'product', 'variant'], name='unique_cart_product_variant')]

    @property
    def unit_price(self):
        if self.variant and self.variant.price_override is not None:
            return self.variant.price_override
        return self.product.current_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def available_stock(self):
        if self.variant:
            return self.variant.stock
        return self.product.stock

    def __str__(self):
        lbl = f" ({self.variant_label})" if self.variant_label else ""
        return f'{self.quantity} × {self.product.name}{lbl}'


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} wishlist'


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='wishlist_items')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['wishlist', 'product'], name='unique_wishlist_product')]

    def __str__(self):
        return self.product.name
