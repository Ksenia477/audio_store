from django import forms

from .models import Shipment


class CheckoutForm(forms.Form):
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Телефон', max_length=40)
    city = forms.CharField(label='Город', max_length=120)
    address = forms.CharField(label='Адрес', max_length=260)
    postal_code = forms.CharField(label='Индекс', max_length=20, required=False)
    delivery_method = forms.ChoiceField(
        label='Доставка',
        choices=Shipment.DeliveryMethod.choices,
        required=False,
        initial=Shipment.DeliveryMethod.COURIER,
    )
    cdek_to_city_code = forms.IntegerField(
        label='Код города СДЭК',
        required=False,
        min_value=1,
        help_text='Можно оставить пустым в mock-режиме.',
    )
    delivery_point = forms.CharField(
        label='Код ПВЗ СДЭК',
        max_length=80,
        required=False,
        help_text='Для доставки в пункт выдачи.',
    )
    comment = forms.CharField(
        label='Комментарий',
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    def clean_delivery_method(self):
        return self.cleaned_data.get('delivery_method') or Shipment.DeliveryMethod.COURIER


def get_checkout_initial(user):
    if not user.is_authenticated:
        return {}

    initial = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
    }
    default_address = user.addresses.filter(is_default=True).first()
    if default_address:
        address_parts = [default_address.street, default_address.house]
        if default_address.apartment:
            address_parts.append(default_address.apartment)
        initial.update(
            {
                'first_name': default_address.full_name.split(' ', 1)[0],
                'last_name': _last_name(default_address.full_name),
                'phone': default_address.phone,
                'city': default_address.city,
                'address': ', '.join(address_parts),
                'postal_code': default_address.postal_code,
                'comment': default_address.comment,
                'delivery_method': Shipment.DeliveryMethod.COURIER,
            },
        )
    return initial


def _last_name(full_name):
    parts = full_name.split(' ', 1)
    if len(parts) == 2:
        return parts[1]
    return ''
