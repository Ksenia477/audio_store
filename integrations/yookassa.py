from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from yookassa import Configuration
from yookassa import Payment as YooKassaPayment

from orders.models import Payment


@dataclass(frozen=True)
class PaymentCreationResult:
    provider: str
    provider_payment_id: str
    status: str
    confirmation_url: str
    raw_response: dict


def is_yookassa_configured():
    return (
        bool(settings.YOOKASSA_SHOP_ID)
        and bool(settings.YOOKASSA_SECRET_KEY)
        and not settings.YOOKASSA_USE_MOCK
    )


def create_payment(order, request, idempotency_key):
    if not is_yookassa_configured():
        return _create_mock_payment(order, request)

    Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
    response = YooKassaPayment.create(
        {
            'amount': {
                'value': f'{order.total_price:.2f}',
                'currency': settings.YOOKASSA_CURRENCY,
            },
            'capture': True,
            'confirmation': {
                'type': 'redirect',
                'return_url': request.build_absolute_uri(
                    reverse('orders:payment_return', kwargs={'pk': order.pk}),
                ),
            },
            'description': f'Заказ #{order.pk}'[:128],
            'metadata': {
                'order_id': str(order.pk),
            },
        },
        str(idempotency_key),
    )
    response_data = dict(response)
    confirmation = response_data.get('confirmation') or {}

    return PaymentCreationResult(
        provider=Payment.Provider.YOOKASSA,
        provider_payment_id=response_data.get('id', ''),
        status=response_data.get('status', Payment.Status.PENDING),
        confirmation_url=confirmation.get('confirmation_url', ''),
        raw_response=response_data,
    )


def find_payment(provider_payment_id):
    if not is_yookassa_configured() or not provider_payment_id:
        return None

    Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
    response = YooKassaPayment.find_one(provider_payment_id)
    return dict(response)


def _create_mock_payment(order, request):
    provider_payment_id = f'mock-{uuid4()}'
    confirmation_url = request.build_absolute_uri(
        reverse('orders:mock_payment', kwargs={'provider_payment_id': provider_payment_id}),
    )
    raw_response = {
        'id': provider_payment_id,
        'status': Payment.Status.PENDING,
        'paid': False,
        'amount': {
            'value': f'{order.total_price:.2f}',
            'currency': settings.YOOKASSA_CURRENCY,
        },
        'confirmation': {
            'type': 'redirect',
            'confirmation_url': confirmation_url,
        },
        'metadata': {
            'order_id': str(order.pk),
        },
        'test': True,
    }

    return PaymentCreationResult(
        provider=Payment.Provider.MOCK,
        provider_payment_id=provider_payment_id,
        status=Payment.Status.PENDING,
        confirmation_url=confirmation_url,
        raw_response=raw_response,
    )
