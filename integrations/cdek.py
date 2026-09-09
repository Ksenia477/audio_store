from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings

from orders.models import Shipment


class CdekError(Exception):
    pass


@dataclass(frozen=True)
class DeliveryQuote:
    provider: str
    delivery_method: str
    tariff_code: int
    price: Decimal
    period_min: int | None
    period_max: int | None
    raw_response: dict


def is_cdek_configured():
    return (
        bool(settings.CDEK_CLIENT_ID)
        and bool(settings.CDEK_CLIENT_SECRET)
        and not settings.CDEK_USE_MOCK
    )


def calculate_delivery(cart_items, delivery_data):
    delivery_method = delivery_data.get('delivery_method') or Shipment.DeliveryMethod.COURIER
    tariff_code = _tariff_code_for_method(delivery_method)

    if not is_cdek_configured():
        return _mock_delivery_quote(delivery_method, tariff_code)

    client = CdekClient()
    payload = _build_tariff_payload(cart_items, delivery_data, tariff_code)
    response_data = client.post('/calculator/tariff', payload)
    price = Decimal(str(response_data.get('delivery_sum') or response_data.get('total_sum') or '0'))

    return DeliveryQuote(
        provider=Shipment.Provider.CDEK,
        delivery_method=delivery_method,
        tariff_code=tariff_code,
        price=price,
        period_min=response_data.get('period_min'),
        period_max=response_data.get('period_max'),
        raw_response=response_data,
    )


def register_order(order, shipment):
    if shipment.provider != Shipment.Provider.CDEK or not is_cdek_configured():
        return _mock_register_response(order, shipment)

    client = CdekClient()
    payload = _build_order_payload(order, shipment)
    shipment.raw_request = payload
    shipment.save(update_fields=['raw_request', 'updated_at'])
    return client.post('/orders', payload)


def get_order_info(shipment):
    if shipment.provider != Shipment.Provider.CDEK or not is_cdek_configured():
        return shipment.raw_response or _mock_register_response(shipment.order, shipment)

    client = CdekClient()
    if shipment.cdek_uuid:
        return client.get(f'/orders/{shipment.cdek_uuid}')
    if shipment.cdek_number:
        return client.get('/orders', params={'cdek_number': shipment.cdek_number})
    raise CdekError('Для проверки статуса нет номера отправления СДЭК.')


class CdekClient:
    def __init__(self):
        self.base_url = settings.CDEK_BASE_URL.rstrip('/')
        self.session = requests.Session()
        self._access_token = None

    def get(self, path, params=None):
        response = self.session.get(
            f'{self.base_url}{path}',
            params=params,
            headers=self._headers(),
            timeout=20,
        )
        return self._handle_response(response)

    def post(self, path, payload):
        response = self.session.post(
            f'{self.base_url}{path}',
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        return self._handle_response(response)

    def _headers(self):
        return {
            'Authorization': f'Bearer {self._token()}',
            'Content-Type': 'application/json',
        }

    def _token(self):
        if self._access_token:
            return self._access_token

        response = self.session.post(
            f'{self.base_url}/oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': settings.CDEK_CLIENT_ID,
                'client_secret': settings.CDEK_CLIENT_SECRET,
            },
            timeout=20,
        )
        data = self._handle_response(response)
        self._access_token = data['access_token']
        return self._access_token

    @staticmethod
    def _handle_response(response):
        try:
            data = response.json()
        except ValueError as exc:
            raise CdekError('СДЭК вернул ответ не в JSON.') from exc

        if response.status_code >= 400:
            raise CdekError(str(data))
        return data


def _build_tariff_payload(cart_items, delivery_data, tariff_code):
    return {
        'tariff_code': tariff_code,
        'from_location': {
            'code': settings.CDEK_FROM_CITY_CODE,
        },
        'to_location': _to_location(delivery_data),
        'packages': [_package_from_cart(cart_items)],
    }


def _build_order_payload(order, shipment):
    package = _package_from_order(order)
    payload = {
        'number': str(order.pk),
        'tariff_code': shipment.tariff_code,
        'recipient': {
            'name': f'{order.first_name} {order.last_name}'.strip(),
            'phones': [{'number': order.phone}],
        },
        'from_location': {
            'code': shipment.from_city_code,
        },
        'to_location': _shipment_to_location(shipment),
        'packages': [package],
    }

    if settings.CDEK_SHIPMENT_POINT:
        payload['shipment_point'] = settings.CDEK_SHIPMENT_POINT
    if shipment.delivery_method == Shipment.DeliveryMethod.PICKUP and shipment.delivery_point:
        payload['delivery_point'] = shipment.delivery_point

    return payload


def _to_location(delivery_data):
    to_city_code = delivery_data.get('cdek_to_city_code')
    if to_city_code:
        return {'code': int(to_city_code)}

    location = {'city': delivery_data.get('city', '')}
    postal_code = delivery_data.get('postal_code')
    if postal_code:
        location['postal_code'] = postal_code
    if delivery_data.get('address'):
        location['address'] = delivery_data['address']
    return location


def _shipment_to_location(shipment):
    if shipment.to_city_code:
        return {'code': shipment.to_city_code, 'address': shipment.recipient_address}

    location = {
        'city': shipment.to_city,
        'address': shipment.recipient_address,
    }
    return location


def _package_from_cart(cart_items):
    weight = max(1, sum(item['quantity'] for item in cart_items)) * settings.CDEK_PACKAGE_WEIGHT_GRAMS
    return {
        'weight': weight,
        'length': settings.CDEK_PACKAGE_LENGTH_CM,
        'width': settings.CDEK_PACKAGE_WIDTH_CM,
        'height': settings.CDEK_PACKAGE_HEIGHT_CM,
    }


def _package_from_order(order):
    items = []
    total_quantity = 0
    for order_item in order.items.all():
        total_quantity += order_item.quantity
        items.append(
            {
                'name': order_item.product_name,
                'ware_key': order_item.product_sku or str(order_item.pk),
                'payment': {'value': 0},
                'cost': float(order_item.unit_price),
                'weight': settings.CDEK_PACKAGE_WEIGHT_GRAMS,
                'amount': order_item.quantity,
            },
        )

    return {
        'number': str(order.pk),
        'weight': max(1, total_quantity) * settings.CDEK_PACKAGE_WEIGHT_GRAMS,
        'length': settings.CDEK_PACKAGE_LENGTH_CM,
        'width': settings.CDEK_PACKAGE_WIDTH_CM,
        'height': settings.CDEK_PACKAGE_HEIGHT_CM,
        'items': items,
    }


def _mock_delivery_quote(delivery_method, tariff_code):
    if delivery_method == Shipment.DeliveryMethod.PICKUP:
        price = Decimal(settings.CDEK_MOCK_PICKUP_PRICE)
        period_min = 2
        period_max = 4
    else:
        price = Decimal(settings.CDEK_MOCK_COURIER_PRICE)
        period_min = 3
        period_max = 5

    return DeliveryQuote(
        provider=Shipment.Provider.MOCK,
        delivery_method=delivery_method,
        tariff_code=tariff_code,
        price=price,
        period_min=period_min,
        period_max=period_max,
        raw_response={
            'mock': True,
            'delivery_sum': str(price),
            'period_min': period_min,
            'period_max': period_max,
            'tariff_code': tariff_code,
        },
    )


def _mock_register_response(order, shipment):
    mock_number = f'MOCK-CDEK-{order.pk}'
    return {
        'mock': True,
        'entity': {
            'uuid': f'mock-shipment-{order.pk}',
            'cdek_number': mock_number,
            'statuses': [
                {
                    'code': 'CREATED',
                    'name': 'Создан',
                },
            ],
        },
        'requests': [],
        'delivery_method': shipment.delivery_method,
    }


def _tariff_code_for_method(delivery_method):
    if delivery_method == Shipment.DeliveryMethod.PICKUP:
        return settings.CDEK_PICKUP_TARIFF_CODE
    return settings.CDEK_COURIER_TARIFF_CODE
