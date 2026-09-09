from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CustomerAddress

User = get_user_model()


class UsersTests(TestCase):
    def test_register_creates_and_logs_in_user(self):
        response = self.client.post(
            reverse('users:register'),
            {
                'username': 'buyer',
                'email': 'buyer@example.com',
                'first_name': 'Анна',
                'last_name': 'Иванова',
                'password1': 'Str0ng-test-pass!',
                'password2': 'Str0ng-test-pass!',
            },
        )

        self.assertRedirects(response, reverse('users:dashboard'))
        self.assertTrue(User.objects.filter(username='buyer').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('users:dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response['Location'])

    def test_profile_update_changes_user_data(self):
        user = User.objects.create_user(
            username='buyer',
            email='old@example.com',
            password='pass',
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('users:profile_update'),
            {
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'email': 'new@example.com',
            },
        )

        self.assertRedirects(response, reverse('users:dashboard'))
        user.refresh_from_db()
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'Мария')

    def test_address_create_saves_default_address(self):
        user = User.objects.create_user(username='buyer', password='pass')
        self.client.force_login(user)

        response = self.client.post(
            reverse('users:address_create'),
            {
                'title': 'Дом',
                'full_name': 'Мария Петрова',
                'phone': '+79990000000',
                'city': 'Москва',
                'street': 'Тверская',
                'house': '1',
                'apartment': '12',
                'postal_code': '101000',
                'comment': '',
                'is_default': 'on',
            },
        )

        self.assertRedirects(response, reverse('users:dashboard'))
        address = CustomerAddress.objects.get(user=user)
        self.assertEqual(address.city, 'Москва')
        self.assertTrue(address.is_default)

    def test_only_one_default_address_per_user(self):
        user = User.objects.create_user(username='buyer', password='pass')
        CustomerAddress.objects.create(
            user=user,
            title='Дом',
            full_name='Мария Петрова',
            phone='+79990000000',
            city='Москва',
            street='Тверская',
            house='1',
            is_default=True,
        )

        second = CustomerAddress.objects.create(
            user=user,
            title='Офис',
            full_name='Мария Петрова',
            phone='+79990000000',
            city='Москва',
            street='Арбат',
            house='2',
            is_default=True,
        )

        self.assertTrue(second.is_default)
        self.assertEqual(CustomerAddress.objects.filter(user=user, is_default=True).count(), 1)
