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

