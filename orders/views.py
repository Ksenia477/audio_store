import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from yookassa.domain.notification import WebhookNotificationFactory

from cart.cart import Cart
from integrations import cdek
from .forms import CheckoutForm, get_checkout_initial
from .models import Order, Payment
from .services import (
    CheckoutError,
    apply_payment_status,
    create_order_from_cart,
    create_payment_for_order,
    register_shipment_with_provider,
    sync_shipment_from_provider,
    sync_payment_from_provider,
)

RECENT_ORDER_SESSION_ID = 'recent_order_ids'


class OrderListView(LoginRequiredMixin, ListView):
    template_name = 'orders/list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return self.request.user.orders.select_related('shipment').prefetch_related('items')


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = 'orders/detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return self.request.user.orders.select_related('shipment').prefetch_related('items', 'payments')


@require_http_methods(['GET', 'POST'])
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)
    if not cart_items:
        messages.error(request, 'Корзина пуста.')
        return redirect('cart:detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = create_order_from_cart(cart, request.user, form.cleaned_data)
            except CheckoutError as error:
                messages.error(request, str(error))
                return redirect('cart:detail')

            recent_order_ids = request.session.get(RECENT_ORDER_SESSION_ID, [])
            request.session[RECENT_ORDER_SESSION_ID] = [order.id, *recent_order_ids[:4]]
            request.session.modified = True
            register_shipment_with_provider(order.shipment)
            messages.success(request, f'Заказ #{order.id} создан.')
            return _redirect_to_payment(order, request)
    else:
        form = CheckoutForm(initial=get_checkout_initial(request.user))
    delivery_quote = None
    try:
        delivery_quote = cdek_quote_for_checkout(cart_items, form)
    except CheckoutError as error:
        messages.error(request, str(error))

    return render(
        request,
        'orders/checkout.html',
        {
            'form': form,
            'cart': cart,
            'cart_items': cart_items,
            'delivery_quote': delivery_quote,
            'checkout_total': cart.get_total_price()
            + (delivery_quote.price if delivery_quote else 0),
        },
    )


def order_complete(request, pk):
    order = _get_visible_order(request, pk)

    return render(request, 'orders/complete.html', {'order': order})


@require_POST
def start_payment(request, pk):
    order = _get_visible_order(request, pk)
    return _redirect_to_payment(order, request)


@require_POST
def sync_shipment(request, pk):
    order = _get_visible_order(request, pk)
    shipment = getattr(order, 'shipment', None)
    if not shipment:
        messages.error(request, 'Для заказа еще нет доставки.')
        return redirect('orders:complete', pk=order.pk)

    try:
        sync_shipment_from_provider(shipment)
    except Exception:
        messages.error(request, 'Не получилось обновить статус доставки.')
    else:
        messages.success(request, 'Статус доставки обновлен.')
    return redirect('orders:complete', pk=order.pk)


def payment_return(request, pk):
    order = _get_visible_order(request, pk)
    payment = order.payments.filter(provider=Payment.Provider.YOOKASSA).first()
    if payment:
        try:
            sync_payment_from_provider(payment)
        except Exception:
            messages.info(request, 'Статус оплаты обновится после уведомления от ЮKassa.')
    return redirect('orders:complete', pk=order.pk)


@require_http_methods(['GET', 'POST'])
def mock_payment(request, provider_payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('order').prefetch_related('order__items'),
        provider=Payment.Provider.MOCK,
        provider_payment_id=provider_payment_id,
    )
    _get_visible_order(request, payment.order_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        raw_response = {
            **payment.raw_response,
            'status': Payment.Status.SUCCEEDED if action == 'succeeded' else Payment.Status.CANCELED,
            'paid': action == 'succeeded',
        }
        if action == 'succeeded':
            payment.mark_succeeded(raw_response)
            messages.success(request, f'Заказ #{payment.order_id} оплачен в тестовом режиме.')
        else:
            payment.mark_canceled(raw_response)
            messages.error(request, 'Тестовый платеж отменен.')
        return redirect('orders:complete', pk=payment.order_id)

    return render(request, 'orders/payments/mock.html', {'payment': payment})


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        notification = WebhookNotificationFactory().create(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return HttpResponseBadRequest('Invalid notification payload')

    payment_data = dict(notification.object)
    event = notification.event
    provider_payment_id = payment_data.get('payment_id') if event == 'refund.succeeded' else payment_data.get('id')
    metadata = payment_data.get('metadata') or {}

    payment = Payment.objects.filter(provider_payment_id=provider_payment_id).select_related('order').first()
    if payment is None and metadata.get('order_id'):
        payment = (
            Payment.objects.filter(order_id=metadata['order_id'])
            .order_by('-created_at')
            .select_related('order')
            .first()
        )
        if payment and provider_payment_id:
            payment.provider_payment_id = provider_payment_id
            payment.provider = Payment.Provider.YOOKASSA
            payment.save(update_fields=['provider_payment_id', 'provider', 'updated_at'])

    if payment:
        apply_payment_status(payment, payment_data, event=event)

    return JsonResponse({'ok': True})


def _redirect_to_payment(order, request):
    try:
        payment = create_payment_for_order(order, request)
    except CheckoutError as error:
        messages.error(request, str(error))
        return redirect('orders:complete', pk=order.pk)
    except Exception:
        messages.error(request, 'Не получилось создать платеж. Попробуй еще раз.')
        return redirect('orders:complete', pk=order.pk)

    if not payment.confirmation_url:
        messages.error(request, 'Платеж создан без ссылки на оплату.')
        return redirect('orders:complete', pk=order.pk)

    return redirect(payment.confirmation_url)


def cdek_quote_for_checkout(cart_items, form):
    data = form.initial.copy()
    if form.is_bound and form.is_valid():
        data.update(form.cleaned_data)
    elif form.is_bound:
        return None
    if cdek.is_cdek_configured() and not data.get('city'):
        return None

    try:
        return cdek.calculate_delivery(cart_items, data)
    except cdek.CdekError as error:
        raise CheckoutError(str(error)) from error


def _get_visible_order(request, pk):
    queryset = Order.objects.select_related('shipment').prefetch_related('items', 'payments')
    if request.user.is_authenticated:
        return get_object_or_404(queryset, pk=pk, user=request.user)

    recent_order_ids = request.session.get(RECENT_ORDER_SESSION_ID, [])
    return get_object_or_404(queryset, pk=pk, id__in=recent_order_ids)
