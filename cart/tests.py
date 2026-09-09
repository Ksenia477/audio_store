from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.urls import reverse

from catalog.models import Category, Product
from .cart import CART_SESSION_ID, Cart


class CartTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Микрофоны', slug='microphones')
        self.product = Product.objects.create(
            category=self.category,
            name='Fifine K688',
            slug='fifine-k688',
            sku='MIC-001',
            short_description='Динамический USB/XLR микрофон',
            price=Decimal('8990.00'),
            stock=3,
        )

    def test_add_product_to_cart_session(self):
        response = self.client.post(
            reverse('cart:add', args=[self.product.id]),
            {'quantity': 2, 'next': reverse('cart:detail')},
        )

        self.assertRedirects(response, reverse('cart:detail'))
        self.assertEqual(
            self.client.session[CART_SESSION_ID][str(self.product.id)]['quantity'],
            2,
        )

    def test_cart_detail_shows_added_product(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})

        response = self.client.get(reverse('cart:detail'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, 'Итого')
        self.assertContains(response, 'quantity-field')
        self.assertContains(response, 'quantity-apply-button')
        self.assertContains(response, 'cart-remove-button')
        self.assertNotContains(response, 'data-auto-submit-form')
        self.assertNotContains(response, 'data-quantity-step')
        self.assertNotContains(response, 'quantity-stepper')
        self.assertNotContains(response, 'quantity-step-button')
        self.assertNotContains(response, 'quantity-adjustments')

    def test_update_product_quantity(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})
        response = self.client.post(
            reverse('cart:update', args=[self.product.id]),
            {'quantity': 3, 'override': 'on'},
        )

        self.assertRedirects(response, reverse('cart:detail'))
        self.assertEqual(
            self.client.session[CART_SESSION_ID][str(self.product.id)]['quantity'],
            3,
        )

    def test_auto_update_product_quantity_does_not_show_success_message(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})
        response = self.client.post(
            reverse('cart:update', args=[self.product.id]),
            {'quantity': 2, 'override': 'on', 'auto_update': 'on'},
            follow=True,
        )

        self.assertEqual(
            self.client.session[CART_SESSION_ID][str(self.product.id)]['quantity'],
            2,
        )
        self.assertNotContains(response, 'Количество обновлено.')

    def test_remove_product_from_cart(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})
        response = self.client.post(reverse('cart:remove', args=[self.product.id]))

        self.assertRedirects(response, reverse('cart:detail'))
        self.assertNotIn(str(self.product.id), self.client.session[CART_SESSION_ID])

    def test_cart_service_clamps_quantity_to_stock(self):
        request = RequestFactory().get('/')
        request.session = self.client.session
        cart = Cart(request)

        cart.add(self.product, quantity=99)

        self.assertEqual(cart.cart[str(self.product.id)]['quantity'], self.product.stock)
