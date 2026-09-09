import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from .models import Order, OrderItem, Payment, Shipment

User = get_user_model()


class OrderViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='pass',
        )
        self.other_user = User.objects.create_user(username='other', password='pass')
        category = Category.objects.create(name='Микрофоны', slug='microphones')
        self.product = Product.objects.create(
            category=category,
            name='Fifine K688',
            slug='fifine-k688',
            price=Decimal('8990.00'),
            stock=3,
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name='Мария',
            last_name='Петрова',
            email='buyer@example.com',
            phone='+79990000000',
            city='Москва',
            address='Тверская, 1',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            product_sku=self.product.sku or '',
            unit_price=self.product.price,
            quantity=2,
        )
        self.order.recalculate_total()

    def test_order_list_requires_login(self):
        response = self.client.get(reverse('orders:list'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response['Location'])

    def test_order_list_shows_user_orders(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('orders:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Заказ #{self.order.id}')
        self.assertContains(response, '17\xa0980 ₽')

    def test_order_detail_is_limited_to_owner(self):
        self.client.force_login(self.other_user)

        response = self.client.get(reverse('orders:detail', args=[self.order.id]))

        self.assertEqual(response.status_code, 404)

    def test_guest_checkout_creates_order_and_clears_cart(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})

        response = self.client.post(
            reverse('orders:checkout'),
            {
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'email': 'guest@example.com',
                'phone': '+79990000000',
                'city': 'Москва',
                'address': 'Тверская, 1',
                'postal_code': '101000',
                'comment': '',
            },
        )

        order = Order.objects.latest('id')
        payment = order.payments.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], payment.confirmation_url)
        self.assertIsNone(order.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_price, Decimal('18570.00'))
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(order.shipment.provider, Shipment.Provider.MOCK)
        self.assertEqual(order.shipment.delivery_price, Decimal('590.00'))
        self.assertEqual(order.shipment.tracking_number, f'MOCK-CDEK-{order.pk}')
        self.assertNotIn('cart', self.client.session)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_guest_can_pay_mock_payment_and_open_completed_order(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})
        response = self.client.post(
            reverse('orders:checkout'),
            {
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'email': 'guest@example.com',
                'phone': '+79990000000',
                'city': 'Москва',
                'address': 'Тверская, 1',
                'postal_code': '',
                'comment': '',
            },
        )
        order = Order.objects.latest('id')
        payment = order.payments.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], payment.confirmation_url)

        pay_response = self.client.post(
            reverse('orders:mock_payment', args=[payment.provider_payment_id]),
            {'action': 'succeeded'},
        )

        self.assertRedirects(pay_response, reverse('orders:complete', args=[order.id]))
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)

        complete_response = self.client.get(reverse('orders:complete', args=[order.id]))

        self.assertEqual(complete_response.status_code, 200)
        self.assertContains(complete_response, f'Заказ #{order.id} создан')

    def test_user_checkout_attaches_order_to_user(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})

        response = self.client.post(
            reverse('orders:checkout'),
            {
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'email': 'buyer@example.com',
                'phone': '+79990000000',
                'city': 'Москва',
                'address': 'Тверская, 1',
                'postal_code': '',
                'comment': '',
            },
        )

        order = Order.objects.latest('id')
        payment = order.payments.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], payment.confirmation_url)
        self.assertEqual(order.user, self.user)

    def test_checkout_redirects_empty_cart_to_cart_page(self):
        response = self.client.get(reverse('orders:checkout'))

        self.assertRedirects(response, reverse('cart:detail'))

    def test_checkout_can_use_pickup_delivery(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})

        self.client.post(
            reverse('orders:checkout'),
            {
                'first_name': 'Мария',
                'last_name': 'Петрова',
                'email': 'guest@example.com',
                'phone': '+79990000000',
                'city': 'Москва',
                'address': 'Тверская, 1',
                'postal_code': '',
                'delivery_method': Shipment.DeliveryMethod.PICKUP,
                'delivery_point': 'MSK123',
                'comment': '',
            },
        )

        order = Order.objects.latest('id')
        shipment = order.shipment
        self.assertEqual(shipment.delivery_method, Shipment.DeliveryMethod.PICKUP)
        self.assertEqual(shipment.delivery_price, Decimal('390.00'))
        self.assertEqual(order.total_price, Decimal('9380.00'))

    def test_sync_mock_shipment_keeps_registered_status(self):
        shipment = Shipment.objects.create(
            order=self.order,
            provider=Shipment.Provider.MOCK,
            delivery_method=Shipment.DeliveryMethod.COURIER,
            status=Shipment.Status.REGISTERED,
            tariff_code=136,
            from_city_code=44,
            to_city='Москва',
            recipient_address='Тверская, 1',
            recipient_phone='+79990000000',
            delivery_price=Decimal('590.00'),
            raw_response={
                'entity': {
                    'cdek_number': 'MOCK-CDEK-1',
                    'statuses': [{'code': 'CREATED'}],
                },
            },
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('orders:sync_shipment', args=[self.order.id]))

        self.assertRedirects(response, reverse('orders:complete', args=[self.order.id]))
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, Shipment.Status.REGISTERED)

    def test_yookassa_webhook_marks_payment_as_paid(self):
        payment = Payment.objects.create(
            order=self.order,
            provider=Payment.Provider.YOOKASSA,
            provider_payment_id='test-payment-id',
            amount=self.order.total_price,
        )
        payload = {
            'type': 'notification',
            'event': 'payment.succeeded',
            'object': {
                'id': 'test-payment-id',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': f'{self.order.total_price:.2f}',
                    'currency': 'RUB',
                },
                'metadata': {
                    'order_id': str(self.order.id),
                },
            },
        }

        response = self.client.post(
            reverse('orders:yookassa_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
