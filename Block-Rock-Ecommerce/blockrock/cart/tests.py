from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product

from .models import Cart, CartItem, Wishlist, WishlistItem


class CartWishlistFlowTests(TestCase):
    password = 'SecurePass!2026'

    def setUp(self):
        self.user = User.objects.create_user(username='ashish', password=self.password)
        self.other_user = User.objects.create_user(username='other', password=self.password)
        self.category = Category.objects.create(name='Audio')
        self.product = Product.objects.create(
            name='Block Rock Headphones',
            description='Noise cancelling wireless headphones.',
            brand='Block Rock',
            category=self.category,
            price=Decimal('199.99'),
            stock=5,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_cart_add_update_and_remove_are_user_scoped(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.slug]), {'quantity': '2'})
        self.assertRedirects(response, reverse('cart_detail'))

        item = CartItem.objects.get(cart__user=self.user, product=self.product)
        self.assertEqual(item.quantity, 2)

        self.client.post(reverse('add_to_cart', args=[self.product.slug]), {'quantity': '1'})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        self.client.post(reverse('update_cart_item', args=[item.pk]), {'action': 'increase'})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

        other_cart = Cart.objects.create(user=self.other_user)
        other_item = CartItem.objects.create(cart=other_cart, product=self.product, quantity=1)
        self.assertEqual(self.client.post(reverse('remove_from_cart', args=[other_item.pk])).status_code, 404)

        response = self.client.post(reverse('remove_from_cart', args=[item.pk]))
        self.assertRedirects(response, reverse('cart_detail'))
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_wishlist_add_move_to_cart_and_remove_are_user_scoped(self):
        response = self.client.post(reverse('add_to_wishlist', args=[self.product.slug]))
        self.assertRedirects(response, reverse('wishlist_detail'))
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).count(), 1)

        self.client.post(reverse('add_to_wishlist', args=[self.product.slug]))
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).count(), 1)

        item = WishlistItem.objects.get(wishlist__user=self.user, product=self.product)
        response = self.client.post(reverse('move_wishlist_to_cart', args=[item.pk]))
        self.assertRedirects(response, reverse('wishlist_detail'))
        self.assertTrue(WishlistItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.user, product=self.product).exists())

        other_wishlist = Wishlist.objects.create(user=self.other_user)
        other_item = WishlistItem.objects.create(wishlist=other_wishlist, product=self.product)
        self.assertEqual(self.client.post(reverse('remove_from_wishlist', args=[other_item.pk])).status_code, 404)

        response = self.client.post(reverse('remove_from_wishlist', args=[item.pk]))
        self.assertRedirects(response, reverse('wishlist_detail'))
        self.assertFalse(WishlistItem.objects.filter(pk=item.pk).exists())
