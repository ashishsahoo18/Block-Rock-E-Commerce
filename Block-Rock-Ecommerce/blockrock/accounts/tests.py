from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Subscriber


class AuthenticationFlowTests(TestCase):
    password = 'SecurePass!2026'

    def setUp(self):
        self.user = User.objects.create_user(
            username='ashish',
            email='ashish@example.com',
            password=self.password,
            first_name='Ashish',
        )

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

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(reverse('login'), {'identifier': self.user.username, 'password': 'not-it'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not recognised')

    def test_private_pages_redirect_to_login_with_next(self):
        for name in ('account', 'profile', 'profile_edit', 'profile_password', 'cart_detail', 'wishlist_detail'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response['Location'])
            self.assertIn('next=', response['Location'])

    def test_logout_requires_post_and_returns_home(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

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
    def _message_texts(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]

    def test_valid_email_subscription(self):
        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'Fan@Example.com'})
        self.assertRedirects(response, reverse('home'))

        subscriber = Subscriber.objects.get(email='fan@example.com')
        self.assertTrue(subscriber.is_active)
        self.assertIsNotNone(subscriber.subscribed_at)
        self.assertIn("You're subscribed! Welcome to Block Rock.", self._message_texts(response))

    def test_duplicate_email_does_not_create_duplicate(self):
        Subscriber.objects.create(email='fan@example.com')

        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'FAN@example.com'})

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(Subscriber.objects.filter(email='fan@example.com').count(), 1)
        self.assertIn("You're already subscribed to Block Rock.", self._message_texts(response))

    def test_inactive_duplicate_reactivates_existing_subscriber(self):
        subscriber = Subscriber.objects.create(email='fan@example.com', is_active=False)

        response = self.client.post(reverse('newsletter_subscribe'), {'email': 'fan@example.com'})

        subscriber.refresh_from_db()
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(subscriber.is_active)
        self.assertEqual(Subscriber.objects.count(), 1)
        self.assertIn("You're subscribed! Welcome to Block Rock.", self._message_texts(response))

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

        self.assertContains(response, 'Be the first to join the Block Rock community.')

    def test_get_request_does_not_create_subscriber(self):
        response = self.client.get(reverse('newsletter_subscribe'))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_csrf_protection_rejects_missing_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

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
