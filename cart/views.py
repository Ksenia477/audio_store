from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Product
from .cart import Cart
from .forms import CartAddProductForm


def cart_detail(request):
    return render(request, 'cart/detail.html', {'cart': Cart(request)})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(
        Product.objects.active(),
        id=product_id,
        category__is_active=True,
    )
    form = CartAddProductForm(request.POST, max_quantity=product.stock)

    if form.is_valid() and product.is_in_stock:
        cart = Cart(request)
        quantity = form.cleaned_data['quantity']
        override = form.cleaned_data['override']
        cart.add(product=product, quantity=quantity, override_quantity=override)
        messages.success(request, f'Добавлено в корзину: {product.name}.')
    else:
        messages.error(request, 'Не получилось добавить товар в корзину.')

    return redirect(_safe_next_url(request, product.get_absolute_url()))


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(
        Product.objects.active(),
        id=product_id,
        category__is_active=True,
    )
    form = CartAddProductForm(request.POST, max_quantity=product.stock)

    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        Cart(request).update(product=product, quantity=quantity)
        if request.POST.get('auto_update') != 'on':
            messages.success(request, 'Количество обновлено.')
    else:
        messages.error(request, 'Проверь количество товара.')

    return redirect('cart:detail')


@require_POST
def cart_remove(request, product_id):
    product = Product.objects.filter(id=product_id).first()
    if product:
        Cart(request).remove(product)
        messages.success(request, f'Удалено из корзины: {product.name}.')
    else:
        Cart(request).remove_by_id(product_id)
        messages.success(request, 'Товар удален из корзины.')

    return redirect('cart:detail')


def _safe_next_url(request, default):
    next_url = request.POST.get('next') or request.GET.get('next') or default
    is_safe = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if is_safe:
        return next_url
    return reverse('cart:detail')
