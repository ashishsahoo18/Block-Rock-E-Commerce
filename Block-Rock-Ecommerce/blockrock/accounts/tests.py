from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


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
