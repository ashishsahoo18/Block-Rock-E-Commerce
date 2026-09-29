from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product
from products.templatetags.currency_filters import rupee_format


class ProductCatalogueAndShopTests(TestCase):
    password = 'SecurePass!2026'

    def setUp(self):
        self.user = User.objects.create_user(
            username='ashish',
            email='ashish@example.com',
            password=self.password,
        )
        self.client.force_login(self.user)
        # Execute seed_products command to populate catalogue
        call_command('seed_products')

    def test_seed_command_creates_exactly_50_active_products(self):
        active_count = Product.objects.filter(is_active=True).count()
        self.assertEqual(active_count, 50)

    def test_all_seeded_products_have_unique_slugs(self):
        active_products = Product.objects.filter(is_active=True)
        slugs = set(active_products.values_list('slug', flat=True))
        self.assertEqual(len(slugs), 50)

    def test_categories_coverage(self):
        category_names = list(Category.objects.filter(is_active=True).values_list('name', flat=True))
        expected_categories = [
            'Smartphones', 'Laptops', 'Audio', 'Wearables',
            'Computer Accessories', 'Gaming', 'Cameras', 'Accessories'
        ]
        for cat_name in expected_categories:
            self.assertIn(cat_name, category_names)

    def test_shop_page_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('products'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('products')}")

    def test_shop_page_renders_paginated_products(self):
        response = self.client.get(reverse('products'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products.html')
        # 12 products per page
        self.assertEqual(len(response.context['products']), 12)
        self.assertEqual(response.context['total_results'], 50)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 5)

    def test_shop_search_filter(self):
        response = self.client.get(reverse('products'), {'search': 'ProBook'})
        self.assertEqual(response.status_code, 200)
        for product in response.context['products']:
            self.assertIn('ProBook', product.name)

    def test_shop_category_filter(self):
        response = self.client.get(reverse('products'), {'category': 'laptops'})
        self.assertEqual(response.status_code, 200)
        for product in response.context['products']:
            self.assertEqual(product.category.slug, 'laptops')

    def test_shop_price_range_filter(self):
        response = self.client.get(reverse('products'), {'min_price': '50000', 'max_price': '80000'})
        self.assertEqual(response.status_code, 200)
        for product in response.context['products']:
            self.assertGreaterEqual(product.price, Decimal('50000'))
            self.assertLessEqual(product.price, Decimal('80000'))

    def test_shop_deal_filter(self):
        response = self.client.get(reverse('products'), {'deal': '1'})
        self.assertEqual(response.status_code, 200)
        for product in response.context['products']:
            self.assertTrue(product.is_deal)

    def test_shop_featured_filter(self):
        response = self.client.get(reverse('products'), {'featured': '1'})
        self.assertEqual(response.status_code, 200)
        for product in response.context['products']:
            self.assertTrue(product.is_featured)

    def test_shop_sorting_low_to_high(self):
        response = self.client.get(reverse('products'), {'sort': 'price_low'})
        self.assertEqual(response.status_code, 200)
        prices = [p.price for p in response.context['products']]
        self.assertEqual(prices, sorted(prices))

    def test_shop_sorting_high_to_low(self):
        response = self.client.get(reverse('products'), {'sort': 'price_high'})
        self.assertEqual(response.status_code, 200)
        prices = [p.price for p in response.context['products']]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_rupee_formatting(self):
        self.assertEqual(rupee_format(64999), '₹64,999')
        self.assertEqual(rupee_format(129999), '₹1,29,999')
        self.assertEqual(rupee_format(699), '₹699')

    def test_product_detail_view(self):
        product = Product.objects.filter(is_active=True).first()
        response = self.client.get(reverse('product_detail', args=[product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, product.name)

    def test_seed_ingot_originals_and_collection_page(self):
        call_command('seed_ingot_originals')
        active_electronics = Product.objects.filter(is_active=True, is_ingot_original=False).count()
        active_originals = Product.objects.filter(is_active=True, is_ingot_original=True).count()
        total_active = Product.objects.filter(is_active=True).count()
        self.assertEqual(active_electronics, 50)
        self.assertEqual(active_originals, 20)
        self.assertEqual(total_active, 70)

        # Test dedicated INGOT Originals collection page
        response = self.client.get(reverse('ingot_originals'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ingot_originals.html')
        self.assertEqual(response.context['total_results'], 20)

    def test_search_autocomplete_api(self):
        response = self.client.get(reverse('search_autocomplete') + '?q=ProBook')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertTrue(len(data['results']) > 0)
        self.assertIn('ProBook', data['results'][0]['name'])

    def test_collection_filter(self):
        call_command('seed_ingot_originals')
        # Filter electronics only
        resp_elect = self.client.get(reverse('products'), {'collection': 'electronics'})
        self.assertEqual(resp_elect.status_code, 200)
        self.assertEqual(resp_elect.context['total_results'], 50)

        # Filter originals only
        resp_orig = self.client.get(reverse('products'), {'collection': 'ingot_originals'})
        self.assertEqual(resp_orig.status_code, 200)
        self.assertEqual(resp_orig.context['total_results'], 20)


class IngotNewFeaturesTests(TestCase):
    password = 'SecurePass!2026'

    def setUp(self):
        self.user = User.objects.create_user(
            username='ingot_tester',
            email='tester@ingot.com',
            password=self.password,
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='T-Shirts', slug='t-shirts', is_ingot_original=True)
        self.product = Product.objects.create(
            name='INGOT Heavyweight Tee',
            slug='ingot-heavyweight-tee',
            category=self.category,
            brand='INGOT',
            price=Decimal('1499.00'),
            compare_at_price=Decimal('2499.00'),
            stock=20,
            is_active=True,
            is_ingot_original=True,
            is_featured=True,
            is_deal=True,
        )

    def test_product_image_ordering_and_primary_selection(self):
        img1 = self.product.images.create(
            image='products/test1.png',
            alt_text='Front Angle',
            sort_order=10,
            is_primary=False,
        )
        img2 = self.product.images.create(
            image='products/test2.png',
            alt_text='Hero Front',
            sort_order=0,
            is_primary=True,
        )
        img3 = self.product.images.create(
            image='products/test3.png',
            alt_text='Back Detail',
            sort_order=5,
            is_primary=False,
        )

        # Primary image URL should point to img2
        self.assertEqual(self.product.primary_image_url, img2.image.url)
        # Secondary image URL should point to img3 (next in sort_order)
        self.assertEqual(self.product.secondary_image_url, img3.image.url)

    def test_product_variant_properties_and_helpers(self):
        v1 = self.product.variants.create(
            size='M',
            color_name='Onyx Black',
            color_hex='#111111',
            stock=10,
            sku='ING-TEE-M-BLK',
        )
        v2 = self.product.variants.create(
            size='L',
            color_name='Onyx Black',
            color_hex='#111111',
            stock=5,
            sku='ING-TEE-L-BLK',
        )
        v3 = self.product.variants.create(
            size='M',
            color_name='Cyan Vapor',
            color_hex='#00f0ff',
            stock=0,
            sku='ING-TEE-M-CYN',
        )

        self.assertTrue(self.product.has_variants)
        self.assertIn('M', self.product.available_sizes)
        self.assertIn('L', self.product.available_sizes)
        # Only in-stock colors should be considered available
        available_colors = [c['name'] for c in self.product.available_colors]
        self.assertIn('Onyx Black', available_colors)

    def test_banner_ordering_and_active_scope(self):
        from products.models import Banner
        b1 = Banner.objects.create(
            title='Banner One',
            sort_order=2,
            is_active=True,
        )
        b2 = Banner.objects.create(
            title='Banner Two',
            sort_order=1,
            is_active=True,
        )
        b3 = Banner.objects.create(
            title='Banner Inactive',
            sort_order=0,
            is_active=False,
        )

        active_banners = list(Banner.objects.filter(is_active=True).order_by('sort_order'))
        self.assertEqual(len(active_banners), 2)
        self.assertEqual(active_banners[0].title, 'Banner Two')
        self.assertEqual(active_banners[1].title, 'Banner One')

    def test_size_chart_model_and_association(self):
        from products.models import SizeChart
        chart = SizeChart.objects.create(
            name='T-Shirts Standard Guide',
            category=self.category,
            chart_data={
                'columns': ['Size', 'Chest (in)', 'Length (in)'],
                'rows': [
                    {'Size': 'S', 'Chest (in)': '38', 'Length (in)': '27'},
                    {'Size': 'M', 'Chest (in)': '40', 'Length (in)': '28'},
                    {'Size': 'L', 'Chest (in)': '42', 'Length (in)': '29'},
                ]
            },
            description='All measurements are taken flat.'
        )
        self.product.size_chart = chart
        self.product.save()

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('size_chart', response.context)
        self.assertEqual(response.context['size_chart'].name, 'T-Shirts Standard Guide')

    def test_cart_add_with_variant(self):
        from cart.models import CartItem
        variant = self.product.variants.create(
            size='XL',
            color_name='Onyx Black',
            color_hex='#111111',
            stock=8,
            sku='ING-TEE-XL-BLK',
        )

        response = self.client.post(
            reverse('add_to_cart', args=[self.product.slug]),
            {'quantity': '2', 'variant_id': str(variant.id)}
        )
        self.assertRedirects(response, reverse('cart_detail'))

        cart_item = CartItem.objects.get(cart__user=self.user, product=self.product)
        self.assertEqual(cart_item.variant, variant)
        self.assertEqual(cart_item.quantity, 2)
        self.assertIn('XL', cart_item.variant_label)

    def test_wishlist_toggle_view(self):
        from cart.models import WishlistItem
        # Toggle Add
        response = self.client.post(
            reverse('toggle_wishlist', args=[self.product.slug]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['in_wishlist'])
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).count(), 1)

        # Toggle Remove
        response = self.client.post(
            reverse('toggle_wishlist', args=[self.product.slug]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['in_wishlist'])
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user, product=self.product).count(), 0)

    def test_variant_stock_decrement_on_order_placement(self):
        from cart.models import Cart, CartItem
        from orders.models import Order
        variant = self.product.variants.create(
            size='M',
            color_name='Onyx Black',
            color_hex='#111111',
            stock=10,
            sku='ING-TEE-M-DEC',
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, variant=variant, quantity=3)

        shipping_data = {
            'shipping_name': 'Ingot Tester',
            'phone': '+91 99999 88888',
            'email': 'tester@ingot.com',
            'address_line1': 'Flat 101, Cyber Heights',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'postal_code': '560001',
            'country': 'India',
            'payment_method': 'Cash on Delivery',
        }

        response = self.client.post(reverse('place_order'), shipping_data)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        order_item = order.items.first()

        # Variant stock should have decremented from 10 to 7
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 7)
        self.assertEqual(order_item.variant, variant)
        self.assertIn('Size: M', order_item.variant_label)


