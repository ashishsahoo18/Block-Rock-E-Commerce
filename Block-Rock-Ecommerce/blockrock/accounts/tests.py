from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from products.admin import ProductAdmin
from products.models import Category, Product

from .models import MarketingCampaign, MarketingEmailDelivery, PromotionAnnouncement, Subscriber
from .services import deliver_pending_campaigns, publish_promotion, queue_product_campaign


class AuthenticationFlowTests(TestCase):
    password = 'SecurePass!2026'

    def setUp(self):
        self.user = User.objects.create_user(
            username='ashish',
            email='ashish@example.com',
            password=self.password,
            first_name='Ashish',
        )

    def test_root_url_logged_out_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_root_url_logged_in_renders_homepage(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_register_creates_hashed_user_and_redirects_to_login(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'username': 'ada',
            'email': 'ada@example.com', 'password1': self.password, 'password2': self.password,
        })
        created = User.objects.get(username='ada')
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(created.check_password(self.password))
        self.assertNotEqual(created.password, self.password)

    def test_register_rejects_duplicate_username_and_email(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Other', 'last_name': 'User', 'username': self.user.username,
            'email': self.user.email, 'password1': self.password, 'password2': self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertContains(response, 'already uses this email')

    def test_login_accepts_email_and_preserves_next(self):
        response = self.client.post(reverse('login'), {
            'identifier': self.user.email, 'password': self.password, 'next': reverse('cart_detail'),
        })
        self.assertRedirects(response, reverse('cart_detail'))
        self.assertEqual(self.client.session.get('_auth_user_id'), str(self.user.pk))

    def test_login_success_without_next_redirects_to_home(self):
        response = self.client.post(reverse('login'), {
            'identifier': self.user.email, 'password': self.password,
        })
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(self.client.session.get('_auth_user_id'), str(self.user.pk))

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(reverse('login'), {'identifier': self.user.username, 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password.')

    def test_login_rejects_unknown_email(self):
        response = self.client.post(reverse('login'), {'identifier': 'unknown@example.com', 'password': self.password})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password.')

    def test_private_pages_redirect_to_login_with_next(self):
        protected_urls = [
            '/', '/shop/', '/cart/', '/wishlist/', '/checkout/', '/orders/', '/account/', '/profile/',
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url} should be protected.")
            self.assertIn(reverse('login'), response['Location'])
            self.assertIn('next=', response['Location'])

    def test_protected_pages_accessible_when_logged_in(self):
        self.client.force_login(self.user)
        protected_urls = [
            '/', '/shop/', '/cart/', '/wishlist/', '/orders/', '/account/', '/profile/',
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"URL {url} should be accessible when logged in.")

    def test_logout_destroys_session_and_redirects_to_login(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

        # Confirm user cannot access protected page after logout
        home_res = self.client.get('/')
        self.assertRedirects(home_res, f"{reverse('login')}?next=/")

    def test_profile_edit_keeps_username_and_validates_unique_email(self):
        second_user = User.objects.create_user(username='second', email='second@example.com', password=self.password)
        self.client.force_login(self.user)
        response = self.client.post(reverse('profile_edit'), {
            'first_name': 'Updated', 'last_name': 'Name', 'email': second_user.email,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already uses this email')
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'ashish')

    def test_password_change_keeps_user_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('profile_password'), {
            'old_password': self.password, 'new_password1': 'AnotherPass!2026', 'new_password2': 'AnotherPass!2026',
        })
        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.client.session.get('_auth_user_id'), str(self.user.pk))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_sends_message_for_matching_email(self):
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset/', mail.outbox[0].body)


class NewsletterSubscriptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sub_user', password='Password123!')
        self.client.force_login(self.user)

    def _message_texts(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]

    def test_valid_email_subscription(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'Fan@Example.com'})
        self.assertRedirects(response, reverse('home'))

        subscriber = Subscriber.objects.get(email='fan@example.com')
        self.assertTrue(subscriber.is_active)
        self.assertIsNotNone(subscriber.subscribed_at)
        self.assertIn("You're subscribed! Welcome to INGOT.", self._message_texts(response))

    def test_duplicate_email_does_not_create_duplicate(self):
        Subscriber.objects.create(email='fan@example.com')

        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'FAN@example.com'})

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(Subscriber.objects.filter(email='fan@example.com').count(), 1)
        self.assertIn("You're already subscribed to INGOT.", self._message_texts(response))

    def test_inactive_duplicate_reactivates_existing_subscriber(self):
        subscriber = Subscriber.objects.create(email='fan@example.com', is_active=False)

        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'fan@example.com'})

        subscriber.refresh_from_db()
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(subscriber.is_active)
        self.assertEqual(Subscriber.objects.count(), 1)
        self.assertIn("You're subscribed! Welcome to INGOT.", self._message_texts(response))

    def test_invalid_email_is_rejected(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'not-an-email'})

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertIn('Please enter a valid email address.', self._message_texts(response))

    def test_empty_email_is_rejected(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': ''})

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertIn('Please enter a valid email address.', self._message_texts(response))

    def test_homepage_displays_active_subscriber_count(self):
        Subscriber.objects.create(email='one@example.com')
        Subscriber.objects.create(email='two@example.com')
        Subscriber.objects.create(email='inactive@example.com', is_active=False)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Join 2+ tech lovers staying updated.')
        self.assertNotContains(response, 'Join 3+ tech lovers staying updated.')

    def test_homepage_displays_zero_subscriber_message(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Be the first to join the INGOT community.')

    def test_get_request_does_not_create_subscriber(self):
        response = self.client.get(reverse('newsletter_subscribe'))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_csrf_protection_rejects_missing_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(reverse('newsletter_subscribe'), {'email': 'fan@example.com'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_subscriber_admin_lists_searches_and_manages_status(self):
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='SecurePass!2026',
        )
        subscriber = Subscriber.objects.create(email='fan@example.com')
        self.client.force_login(admin_user)

        changelist_url = reverse('admin:accounts_subscriber_changelist')
        response = self.client.get(changelist_url, {'q': 'fan@example.com'})
        self.assertContains(response, 'fan@example.com')

        self.client.post(changelist_url, {
            'action': 'mark_inactive',
            '_selected_action': [str(subscriber.pk)],
            'index': '0',
        })
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

        self.client.post(changelist_url, {
            'action': 'mark_active',
            '_selected_action': [str(subscriber.pk)],
            'index': '0',
        })
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)


class NewsletterEmailNotificationTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='email_admin',
            email='email-admin@example.com',
            password='SecurePass!2026',
        )
        self.category = Category.objects.create(name='Email notification category')
        self.request_factory = RequestFactory()

    def _product(self, *, active=True, name='Newsletter product'):
        return Product.objects.create(
            name=name,
            category=self.category,
            brand='INGOT',
            description='A product used to test newsletter notifications.',
            short_description='Newsletter-ready product.',
            price=Decimal('1499.00'),
            stock=3,
            is_active=active,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        NEWSLETTER_SEND_WELCOME_EMAIL=True,
    )
    def test_subscription_sends_one_welcome_email_with_unsubscribe_link(self):
        user = User.objects.create_user(username='welcome_user', password='Password123!')
        self.client.force_login(user)

        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'welcome@example.com'})

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(len(mail.outbox), 1)
        subscriber = Subscriber.objects.get(email='welcome@example.com')
        self.assertEqual(mail.outbox[0].to, ['welcome@example.com'])
        self.assertIn(str(subscriber.unsubscribe_token), mail.outbox[0].body)
        self.assertIsNotNone(subscriber.welcome_email_sent_at)

    def test_unsubscribe_requires_post_and_deactivates_subscriber(self):
        subscriber = Subscriber.objects.create(email='unsubscribe@example.com')
        url = reverse('newsletter_unsubscribe', kwargs={'token': subscriber.unsubscribe_token})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)

        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        self.client.post(url)
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

    def test_new_active_admin_product_queues_one_campaign_without_sending(self):
        product = Product(
            name='Admin-created email product',
            category=self.category,
            brand='INGOT',
            description='Created through Django Admin.',
            price=Decimal('999.00'),
            stock=1,
            is_active=True,
        )
        request = self.request_factory.post('/admin/products/product/add/')
        request.user = self.admin_user
        product_admin = ProductAdmin(Product, admin.site)

        with patch.object(ProductAdmin, 'message_user'):
            product_admin.save_model(request, product, form=None, change=False)
            product.name = 'Edited product name'
            product_admin.save_model(request, product, form=None, change=True)

        self.assertEqual(MarketingCampaign.objects.filter(product=product).count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', SITE_URL='https://shop.example')
    def test_product_campaign_delivers_individually_once_and_excludes_inactive_subscribers(self):
        active_subscriber = Subscriber.objects.create(email='active@example.com')
        second_active_subscriber = Subscriber.objects.create(email='second-active@example.com')
        Subscriber.objects.create(email='inactive@example.com', is_active=False)
        product = self._product()
        campaign, created = queue_product_campaign(product)

        self.assertTrue(created)
        first_result = deliver_pending_campaigns()
        second_result = deliver_pending_campaigns()

        self.assertEqual(first_result['sent'], 2)
        self.assertEqual(second_result['sent'], 0)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            {tuple(message.to) for message in mail.outbox},
            {(active_subscriber.email,), (second_active_subscriber.email,)},
        )
        for message in mail.outbox:
            self.assertEqual(message.bcc, [])
            self.assertIn(product.name, message.subject)
            self.assertIn('https://shop.example/products/', message.body)
        delivery = MarketingEmailDelivery.objects.get(campaign=campaign, subscriber=active_subscriber)
        self.assertEqual(delivery.status, MarketingEmailDelivery.Status.SENT)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_inactive_product_campaign_is_cancelled_without_sending(self):
        Subscriber.objects.create(email='subscriber@example.com')
        product = self._product()
        campaign, _ = queue_product_campaign(product)
        product.is_active = False
        product.save(update_fields=['is_active'])

        result = deliver_pending_campaigns()

        campaign.refresh_from_db()
        self.assertEqual(result['sent'], 0)
        self.assertEqual(campaign.status, MarketingCampaign.Status.CANCELLED)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_explicit_promotion_publish_queues_and_sends_one_campaign(self):
        subscriber = Subscriber.objects.create(email='promotion@example.com')
        promotion = PromotionAnnouncement.objects.create(
            title='A real promotion',
            message='A message written by the administrator.',
            destination_url='/shop/',
        )

        self.assertFalse(MarketingCampaign.objects.exists())
        campaign, created = publish_promotion(promotion)
        _, created_again = publish_promotion(promotion)
        result = deliver_pending_campaigns()

        promotion.refresh_from_db()
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertTrue(promotion.is_published)
        self.assertIsNotNone(promotion.published_at)
        self.assertEqual(result['sent'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [subscriber.email])
        self.assertEqual(MarketingCampaign.objects.filter(promotion=promotion).count(), 1)
        self.assertEqual(campaign.campaign_type, MarketingCampaign.CampaignType.PROMOTION)

    def test_delivery_failure_is_recorded_without_exposing_backend_details(self):
        subscriber = Subscriber.objects.create(email='failure@example.com')
        campaign, _ = queue_product_campaign(self._product())

        with patch('accounts.services._send_email', side_effect=RuntimeError('SMTP secret should not be stored')):
            result = deliver_pending_campaigns()

        delivery = MarketingEmailDelivery.objects.get(campaign=campaign, subscriber=subscriber)
        campaign.refresh_from_db()
        self.assertEqual(result['failed'], 1)
        self.assertEqual(delivery.status, MarketingEmailDelivery.Status.FAILED)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.last_error, 'Email backend error: RuntimeError')
        self.assertEqual(campaign.status, MarketingCampaign.Status.PARTIAL)
