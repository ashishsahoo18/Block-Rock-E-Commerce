from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from orders.services import calculate_shipping_fee
from products.models import Category, Product


class OrderSystemTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123!',
            first_name='Alex',
            last_name='Mercer',
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123!',
        )

        self.category = Category.objects.create(name='Electronics', slug='electronics')

        self.product1 = Product.objects.create(
            name='Audio-Technica M50x',
            slug='audio-technica-m50x',
            brand='Audio-Technica',
            category=self.category,
            price=Decimal('1200.00'),
            discount_price=Decimal('1000.00'),
            stock=10,
            is_active=True,
        )

        self.product2 = Product.objects.create(
            name='Gaming Mouse',
            slug='gaming-mouse',
            brand='Logitech',
            category=self.category,
            price=Decimal('400.00'),
            discount_price=None,
            stock=5,
            is_active=True,
        )

        self.valid_shipping_data = {
            'shipping_name': 'Alex Mercer',
            'phone': '+91 98765 43210',
            'email': 'user1@example.com',
            'address_line1': '123 Tech Park',
            'address_line2': 'Suite 404',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'postal_code': '400001',
            'country': 'India',
            'payment_method': 'Cash on Delivery',
        }

    # 1. Order model creation
    def test_order_model_creation(self):
        order = Order.objects.create(
            user=self.user1,
            shipping_name='Alex Mercer',
            phone='1234567890',
            email='user1@example.com',
            address_line1='Street 1',
            city='City',
            state='State',
            postal_code='10000',
            country='India',
            subtotal=Decimal('1000.00'),
            shipping_fee=Decimal('0.00'),
            total=Decimal('1000.00'),
        )
        self.assertTrue(order.order_number.startswith('BR-'))
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.user, self.user1)

    # 2. Unique order number
    def test_unique_order_number(self):
        order1 = Order.objects.create(
            user=self.user1, shipping_name='A', phone='1', email='a@a.com',
            address_line1='A', city='C', state='S', postal_code='1', country='I',
            subtotal=Decimal('10'), shipping_fee=Decimal('0'), total=Decimal('10')
        )
        order2 = Order.objects.create(
            user=self.user1, shipping_name='B', phone='2', email='b@b.com',
            address_line1='B', city='C', state='S', postal_code='2', country='I',
            subtotal=Decimal('20'), shipping_fee=Decimal('0'), total=Decimal('20')
        )
        self.assertNotEqual(order1.order_number, order2.order_number)

    # 3. OrderItem creation
    def test_order_item_creation(self):
        order = Order.objects.create(
            user=self.user1, shipping_name='A', phone='1', email='a@a.com',
            address_line1='A', city='C', state='S', postal_code='1', country='I',
            subtotal=Decimal('1000.00'), shipping_fee=Decimal('0.00'), total=Decimal('1000.00')
        )
        item = OrderItem.objects.create(
            order=order, product=self.product1, product_name=self.product1.name,
            price=Decimal('1000.00'), quantity=2
        )
        self.assertEqual(item.line_total, Decimal('2000.00'))

    # 4. Correct line totals
    def test_correct_line_totals(self):
        order = Order.objects.create(
            user=self.user1, shipping_name='A', phone='1', email='a@a.com',
            address_line1='A', city='C', state='S', postal_code='1', country='I',
            subtotal=Decimal('800.00'), shipping_fee=Decimal('99.00'), total=Decimal('899.00')
        )
        item = OrderItem.objects.create(
            order=order, product=self.product2, product_name=self.product2.name,
            price=Decimal('400.00'), quantity=2
        )
        self.assertEqual(item.line_total, Decimal('800.00'))

    # 5. Checkout requires authentication
    def test_checkout_requires_authentication(self):
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('checkout')}")

    # 6. Empty cart cannot checkout successfully
    def test_empty_cart_cannot_checkout(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, reverse('cart_detail'))

        post_response = self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertRedirects(post_response, reverse('cart_detail'))
        self.assertEqual(Order.objects.count(), 0)

    # 7. Valid checkout creates an order
    def test_valid_checkout_creates_order(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        response = self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertRedirects(response, reverse('order_confirmation', kwargs={'order_number': order.order_number}))

    # 8. Correct order total is calculated server-side
    def test_server_calculated_order_totals(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product2, quantity=2)

        self.client.post(reverse('place_order'), self.valid_shipping_data)
        order = Order.objects.first()
        self.assertEqual(order.subtotal, Decimal('800.00'))
        self.assertEqual(order.shipping_fee, Decimal('99.00'))
        self.assertEqual(order.total, Decimal('899.00'))

    # 9. Correct stock is reduced
    def test_stock_is_reduced(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=3)

        initial_stock = self.product1.stock
        self.client.post(reverse('place_order'), self.valid_shipping_data)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock - 3)

    # 10. Cart is cleared after successful order
    def test_cart_cleared_after_order(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertEqual(cart.items.count(), 0)

    # 11. Insufficient stock prevents order creation
    def test_insufficient_stock_prevents_order(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=20)

        response = self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertRedirects(response, reverse('checkout'))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(cart.items.count(), 1)

    # 12. Stock never becomes negative
    def test_stock_never_becomes_negative(self):
        self.product1.stock = 2
        self.product1.save()

        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=5)

        self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.product1.refresh_from_db()
        self.assertGreaterEqual(self.product1.stock, 0)
        self.assertEqual(self.product1.stock, 2)

    # 13. Failed transaction does not partially create an order
    def test_failed_transaction_rollback(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=15)

        self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(cart.items.count(), 1)

    # 14. User can only see their own orders in My Orders
    def test_user_can_only_see_own_orders(self):
        order1 = Order.objects.create(
            user=self.user1, shipping_name='A', phone='1', email='a@a.com',
            address_line1='A', city='C', state='S', postal_code='1', country='I',
            subtotal=Decimal('100'), shipping_fee=Decimal('0'), total=Decimal('100')
        )
        order2 = Order.objects.create(
            user=self.user2, shipping_name='B', phone='2', email='b@b.com',
            address_line1='B', city='C', state='S', postal_code='2', country='I',
            subtotal=Decimal('200'), shipping_fee=Decimal('0'), total=Decimal('200')
        )

        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('order_list'))
        self.assertContains(response, order1.order_number)
        self.assertNotContains(response, order2.order_number)

    # 15. Another user cannot access someone else's order
    def test_user_cannot_access_other_user_order(self):
        order1 = Order.objects.create(
            user=self.user1, shipping_name='A', phone='1', email='a@a.com',
            address_line1='A', city='C', state='S', postal_code='1', country='I',
            subtotal=Decimal('100'), shipping_fee=Decimal('0'), total=Decimal('100')
        )

        self.client.login(username='user2', password='Password123!')
        response = self.client.get(reverse('order_detail', kwargs={'order_number': order1.order_number}))
        self.assertEqual(response.status_code, 404)

        conf_response = self.client.get(reverse('order_confirmation', kwargs={'order_number': order1.order_number}))
        self.assertEqual(conf_response.status_code, 404)

    # 16. Place-order endpoint rejects GET
    def test_place_order_rejects_get(self):
        self.client.login(username='user1', password='Password123!')
        response = self.client.get(reverse('place_order'))
        self.assertEqual(response.status_code, 405)

    # 17. CSRF protection remains enabled
    def test_csrf_protection_enabled(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        response = client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertEqual(response.status_code, 403)

    # 18. Product price manipulation from client side cannot change final order price
    def test_client_cannot_manipulate_price(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=1)

        tampered_data = self.valid_shipping_data.copy()
        tampered_data['subtotal'] = '1.00'
        tampered_data['total'] = '1.00'
        tampered_data['price'] = '1.00'

        self.client.post(reverse('place_order'), tampered_data)
        order = Order.objects.first()
        self.assertEqual(order.subtotal, Decimal('1000.00'))
        self.assertEqual(order.total, Decimal('1000.00'))

    # 19. Quantity manipulation cannot exceed available stock
    def test_quantity_manipulation_cannot_exceed_stock(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product2, quantity=10)

        response = self.client.post(reverse('place_order'), self.valid_shipping_data)
        self.assertEqual(Order.objects.count(), 0)

    # 20. Multiple order items are stored correctly
    def test_multiple_order_items_stored_correctly(self):
        self.client.login(username='user1', password='Password123!')
        cart = Cart.objects.create(user=self.user1)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=2)
        CartItem.objects.create(cart=cart, product=self.product2, quantity=1)

        self.client.post(reverse('place_order'), self.valid_shipping_data)
        order = Order.objects.first()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.subtotal, Decimal('2400.00'))
        self.assertEqual(order.shipping_fee, Decimal('0.00'))
        self.assertEqual(order.total, Decimal('2400.00'))
