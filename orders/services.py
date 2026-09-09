from django.conf import settings
from django.db import transaction

from catalog.models import Product
from integrations import cdek
from integrations import yookassa
from .models import Order, OrderItem, Payment, Shipment


class CheckoutError(Exception):
    pass


@transaction.atomic
def create_order_from_cart(cart, user, cleaned_data, delivery_quote=None):
    cart_items = list(cart)
    if not cart_items:
        raise CheckoutError('Корзина пуста.')

    if delivery_quote is None:
        try:
            delivery_quote = cdek.calculate_delivery(cart_items, cleaned_data)
        except cdek.CdekError as error:
            raise CheckoutError(str(error)) from error

    product_ids = [item['product'].id for item in cart_items]
    products = (
        Product.objects.select_for_update()
        .active()
        .filter(id__in=product_ids, category__is_active=True)
    )
    product_map = {product.id: product for product in products}

    order = Order.objects.create(
        user=user if user.is_authenticated else None,
        first_name=cleaned_data['first_name'],
        last_name=cleaned_data.get('last_name', ''),
        email=cleaned_data['email'],
        phone=cleaned_data['phone'],
        city=cleaned_data['city'],
        address=cleaned_data['address'],
        postal_code=cleaned_data.get('postal_code', ''),
        comment=cleaned_data.get('comment', ''),
    )

    total_price = 0
    order_items = []
    products_to_update = []

    for item in cart_items:
        original_product = item['product']
        product = product_map.get(original_product.id)
        if product is None:
            raise CheckoutError(f'Товар недоступен: {original_product.name}.')

        quantity = item['quantity']
        if product.stock < quantity:
            raise CheckoutError(f'Недостаточно товара на складе: {product.name}.')

        order_item = OrderItem(
            order=order,
            product=product,
            product_name=product.name,
            product_sku=product.sku or '',
            unit_price=product.price,
            quantity=quantity,
        )
        order_items.append(order_item)
        total_price += order_item.total_price

        product.stock -= quantity
        products_to_update.append(product)

    OrderItem.objects.bulk_create(order_items)
    Product.objects.bulk_update(products_to_update, ['stock'])
    shipment = create_shipment_for_order(order, cleaned_data, delivery_quote, save_total=False)
    order.total_price = total_price + shipment.delivery_price
    order.save(update_fields=['total_price', 'updated_at'])
    cart.clear()

    return order


def create_shipment_for_order(order, cleaned_data, delivery_quote, save_total=True):
    shipment = Shipment.objects.create(
        order=order,
        provider=delivery_quote.provider,
        delivery_method=delivery_quote.delivery_method,
        tariff_code=delivery_quote.tariff_code,
        from_city_code=settings.CDEK_FROM_CITY_CODE,
        to_city=cleaned_data['city'],
        to_city_code=cleaned_data.get('cdek_to_city_code'),
        recipient_address=cleaned_data['address'],
        recipient_phone=cleaned_data['phone'],
        delivery_point=cleaned_data.get('delivery_point', ''),
        delivery_price=delivery_quote.price,
        period_min=delivery_quote.period_min,
        period_max=delivery_quote.period_max,
        raw_response=delivery_quote.raw_response,
    )

    if save_total:
        order.recalculate_total()
    return shipment


def register_shipment_with_provider(shipment):
    try:
        response_data = cdek.register_order(shipment.order, shipment)
    except cdek.CdekError as error:
        shipment.raw_response = {**shipment.raw_response, 'registration_error': str(error)}
        shipment.save(update_fields=['raw_response', 'updated_at'])
    else:
        shipment.mark_registered(response_data)
    return shipment


def create_payment_for_order(order, request):
    if order.payment_status == Order.PaymentStatus.PAID:
        raise CheckoutError('Заказ уже оплачен.')

    existing_payment = (
        order.payments.filter(
            status__in=[Payment.Status.PENDING, Payment.Status.WAITING_FOR_CAPTURE],
        )
        .exclude(confirmation_url='')
        .first()
    )
    if existing_payment:
        return existing_payment

    payment = Payment.objects.create(
        order=order,
        amount=order.total_price,
        currency=settings.YOOKASSA_CURRENCY,
    )
    result = yookassa.create_payment(order, request, payment.idempotency_key)

    payment.provider = result.provider
    payment.provider_payment_id = result.provider_payment_id
    payment.status = _normalize_payment_status(result.status)
    payment.confirmation_url = result.confirmation_url
    payment.raw_response = result.raw_response
    payment.save(
        update_fields=[
            'provider',
            'provider_payment_id',
            'status',
            'confirmation_url',
            'raw_response',
            'updated_at',
        ],
    )
    return payment


def sync_payment_from_provider(payment):
    if payment.provider != Payment.Provider.YOOKASSA:
        return payment

    response_data = yookassa.find_payment(payment.provider_payment_id)
    if not response_data:
        return payment

    apply_payment_status(payment, response_data)
    return payment


def sync_shipment_from_provider(shipment):
    response_data = cdek.get_order_info(shipment)
    shipment.apply_cdek_status(response_data)
    return shipment


def apply_payment_status(payment, raw_response, event=None):
    if event == 'refund.succeeded':
        payment.raw_response = raw_response
        payment.save(update_fields=['raw_response', 'updated_at'])
        payment.order.payment_status = Order.PaymentStatus.REFUNDED
        payment.order.save(update_fields=['payment_status', 'updated_at'])
        return payment

    status = _normalize_payment_status(raw_response.get('status', payment.status))
    if status == Payment.Status.SUCCEEDED:
        payment.mark_succeeded(raw_response)
    elif status == Payment.Status.CANCELED:
        payment.mark_canceled(raw_response)
    else:
        payment.status = status
        payment.raw_response = raw_response
        payment.save(update_fields=['status', 'raw_response', 'updated_at'])
    return payment


def _normalize_payment_status(status):
    valid_statuses = {choice.value for choice in Payment.Status}
    if status in valid_statuses:
        return status
    return Payment.Status.PENDING
