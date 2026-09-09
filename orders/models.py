from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from uuid import uuid4

from catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтвержден'
        PROCESSING = 'processing', 'В обработке'
        SHIPPED = 'shipped', 'Передан в доставку'
        COMPLETED = 'completed', 'Завершен'
        CANCELLED = 'cancelled', 'Отменен'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        REFUNDED = 'refunded', 'Возвращен'

    class ShipmentStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает передачи'
        IN_TRANSIT = 'in_transit', 'В пути'
        READY_FOR_PICKUP = 'ready_for_pickup', 'Готов к выдаче'
        DELIVERED = 'delivered', 'Доставлен'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='пользователь',
        related_name='orders',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    first_name = models.CharField('имя', max_length=150)
    last_name = models.CharField('фамилия', max_length=150, blank=True)
    email = models.EmailField('email')
    phone = models.CharField('телефон', max_length=40)
    city = models.CharField('город', max_length=120)
    address = models.CharField('адрес', max_length=260)
    postal_code = models.CharField('индекс', max_length=20, blank=True)
    comment = models.CharField('комментарий', max_length=300, blank=True)
    status = models.CharField(
        'статус заказа',
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    payment_status = models.CharField(
        'статус оплаты',
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    shipment_status = models.CharField(
        'статус доставки',
        max_length=24,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.PENDING,
    )
    total_price = models.DecimalField('сумма', max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлен', auto_now=True)

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.pk}"

    def get_absolute_url(self):
        return reverse('orders:detail', kwargs={'pk': self.pk})

    def recalculate_total(self, save=True):
        total = sum(item.total_price for item in self.items.all())
        shipment = getattr(self, 'shipment', None)
        if shipment:
            total += shipment.delivery_price
        self.total_price = total
        if save:
            self.save(update_fields=['total_price', 'updated_at'])
        return self.total_price


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name='заказ',
        related_name='items',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        verbose_name='товар',
        blank=True,
        null=True,
        related_name='order_items',
        on_delete=models.SET_NULL,
    )
    product_name = models.CharField('название товара', max_length=220)
    product_sku = models.CharField('артикул', max_length=80, blank=True)
    unit_price = models.DecimalField('цена за шт.', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('количество')

    class Meta:
        verbose_name = 'позиция заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    class Provider(models.TextChoices):
        YOOKASSA = 'yookassa', 'ЮKassa'
        MOCK = 'mock', 'Локальная тестовая оплата'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает оплаты'
        WAITING_FOR_CAPTURE = 'waiting_for_capture', 'Ожидает подтверждения'
        SUCCEEDED = 'succeeded', 'Успешно'
        CANCELED = 'canceled', 'Отменен'

    order = models.ForeignKey(
        Order,
        verbose_name='заказ',
        related_name='payments',
        on_delete=models.CASCADE,
    )
    provider = models.CharField(
        'провайдер',
        max_length=24,
        choices=Provider.choices,
        default=Provider.YOOKASSA,
    )
    provider_payment_id = models.CharField(
        'id платежа у провайдера',
        max_length=120,
        blank=True,
        null=True,
        unique=True,
    )
    status = models.CharField(
        'статус',
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount = models.DecimalField('сумма', max_digits=10, decimal_places=2)
    currency = models.CharField('валюта', max_length=3, default='RUB')
    confirmation_url = models.URLField('ссылка на оплату', max_length=500, blank=True)
    idempotency_key = models.UUIDField(
        'ключ идемпотентности',
        default=uuid4,
        editable=False,
        unique=True,
    )
    raw_response = models.JSONField('ответ провайдера', default=dict, blank=True)
    paid_at = models.DateTimeField('оплачен', blank=True, null=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлен', auto_now=True)

    class Meta:
        verbose_name = 'платеж'
        verbose_name_plural = 'платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Платеж #{self.pk} для заказа #{self.order_id}"

    def mark_succeeded(self, raw_response=None):
        self.status = self.Status.SUCCEEDED
        self.paid_at = timezone.now()
        if raw_response is not None:
            self.raw_response = raw_response
        self.save(update_fields=['status', 'paid_at', 'raw_response', 'updated_at'])
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.save(update_fields=['payment_status', 'updated_at'])

    def mark_canceled(self, raw_response=None):
        self.status = self.Status.CANCELED
        if raw_response is not None:
            self.raw_response = raw_response
        self.save(update_fields=['status', 'raw_response', 'updated_at'])


class Shipment(models.Model):
    class Provider(models.TextChoices):
        CDEK = 'cdek', 'СДЭК'
        MOCK = 'mock', 'Локальная тестовая доставка'

    class DeliveryMethod(models.TextChoices):
        COURIER = 'courier', 'Курьером'
        PICKUP = 'pickup', 'Пункт выдачи'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает передачи'
        REGISTERED = 'registered', 'Зарегистрирована'
        IN_TRANSIT = 'in_transit', 'В пути'
        READY_FOR_PICKUP = 'ready_for_pickup', 'Готова к выдаче'
        DELIVERED = 'delivered', 'Доставлена'
        CANCELED = 'canceled', 'Отменена'

    order = models.OneToOneField(
        Order,
        verbose_name='заказ',
        related_name='shipment',
        on_delete=models.CASCADE,
    )
    provider = models.CharField(
        'провайдер',
        max_length=24,
        choices=Provider.choices,
        default=Provider.CDEK,
    )
    delivery_method = models.CharField(
        'способ доставки',
        max_length=24,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.COURIER,
    )
    status = models.CharField(
        'статус',
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    tariff_code = models.PositiveIntegerField('код тарифа')
    from_city_code = models.PositiveIntegerField('город отправления')
    to_city = models.CharField('город получателя', max_length=120)
    to_city_code = models.PositiveIntegerField('код города получателя', blank=True, null=True)
    recipient_address = models.CharField('адрес доставки', max_length=260)
    recipient_phone = models.CharField('телефон получателя', max_length=40)
    delivery_point = models.CharField('код ПВЗ', max_length=80, blank=True)
    delivery_price = models.DecimalField('стоимость доставки', max_digits=10, decimal_places=2)
    period_min = models.PositiveIntegerField('срок от, дней', blank=True, null=True)
    period_max = models.PositiveIntegerField('срок до, дней', blank=True, null=True)
    cdek_uuid = models.CharField('uuid СДЭК', max_length=120, blank=True)
    cdek_number = models.CharField('номер СДЭК', max_length=120, blank=True)
    tracking_number = models.CharField('трек-номер', max_length=120, blank=True)
    raw_request = models.JSONField('запрос в СДЭК', default=dict, blank=True)
    raw_response = models.JSONField('ответ СДЭК', default=dict, blank=True)
    registered_at = models.DateTimeField('зарегистрирована', blank=True, null=True)
    created_at = models.DateTimeField('создана', auto_now_add=True)
    updated_at = models.DateTimeField('обновлена', auto_now=True)

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Доставка заказа #{self.order_id}"

    def mark_registered(self, raw_response):
        self.status = self.Status.REGISTERED
        self.raw_response = raw_response
        self.registered_at = timezone.now()
        entity = raw_response.get('entity') or {}
        self.cdek_uuid = entity.get('uuid') or self.cdek_uuid
        self.cdek_number = entity.get('cdek_number') or self.cdek_number
        self.tracking_number = self.cdek_number or self.tracking_number
        self.save(
            update_fields=[
                'status',
                'raw_response',
                'registered_at',
                'cdek_uuid',
                'cdek_number',
                'tracking_number',
                'updated_at',
            ],
        )
        self.order.shipment_status = Order.ShipmentStatus.PENDING
        self.order.save(update_fields=['shipment_status', 'updated_at'])

    def apply_cdek_status(self, raw_response):
        self.raw_response = raw_response
        entity = raw_response.get('entity') or {}
        statuses = entity.get('statuses') or []
        latest_status = statuses[-1] if statuses else {}
        code = (latest_status.get('code') or '').upper()
        self.status = _map_cdek_status(code, self.status)
        self.cdek_number = entity.get('cdek_number') or self.cdek_number
        self.tracking_number = self.cdek_number or self.tracking_number
        self.save(update_fields=['status', 'raw_response', 'cdek_number', 'tracking_number', 'updated_at'])

        self.order.shipment_status = _map_order_shipment_status(self.status)
        self.order.save(update_fields=['shipment_status', 'updated_at'])


def _map_cdek_status(code, default):
    if code in {'CREATED', 'ACCEPTED'}:
        return Shipment.Status.REGISTERED
    if code in {'RECEIVED_AT_SHIPMENT_WAREHOUSE', 'READY_FOR_SHIPMENT_IN_SENDER_CITY', 'TAKEN_BY_TRANSPORTER_FROM_SENDER_CITY', 'SENT_TO_RECIPIENT_CITY', 'ACCEPTED_IN_RECIPIENT_CITY'}:
        return Shipment.Status.IN_TRANSIT
    if code in {'READY_FOR_PICKUP', 'ACCEPTED_AT_PICK_UP_POINT'}:
        return Shipment.Status.READY_FOR_PICKUP
    if code in {'DELIVERED', 'HANDED_TO_RECIPIENT'}:
        return Shipment.Status.DELIVERED
    if code in {'INVALID', 'NOT_DELIVERED', 'RETURNED'}:
        return Shipment.Status.CANCELED
    return default


def _map_order_shipment_status(status):
    if status == Shipment.Status.IN_TRANSIT:
        return Order.ShipmentStatus.IN_TRANSIT
    if status == Shipment.Status.READY_FOR_PICKUP:
        return Order.ShipmentStatus.READY_FOR_PICKUP
    if status == Shipment.Status.DELIVERED:
        return Order.ShipmentStatus.DELIVERED
    return Order.ShipmentStatus.PENDING
