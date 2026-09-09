from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .forms import CustomerAddressForm, UserRegistrationForm, UserUpdateForm
from .models import CustomerAddress


class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'Аккаунт создан.')
        return response


class UserLoginView(LoginView):
    template_name = 'users/login.html'


class UserLogoutView(LogoutView):
    pass


class UserPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'


@login_required
def dashboard(request):
    profile_form = UserUpdateForm(instance=request.user)
    address_form = CustomerAddressForm(
        initial={
            'full_name': request.user.get_full_name() or request.user.username,
            'is_default': not request.user.addresses.exists(),
        },
    )
    recent_orders = request.user.orders.prefetch_related('items')[:5]

    return render(
        request,
        'users/dashboard.html',
        {
            'profile_form': profile_form,
            'address_form': address_form,
            'addresses': request.user.addresses.all(),
            'recent_orders': recent_orders,
        },
    )


@require_POST
@login_required
def profile_update(request):
    form = UserUpdateForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Данные профиля обновлены.')
    else:
        messages.error(request, 'Проверь данные профиля.')
    return redirect('users:dashboard')


@require_POST
@login_required
def address_create(request):
    form = CustomerAddressForm(request.POST)
    if form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        messages.success(request, 'Адрес сохранен.')
    else:
        messages.error(request, 'Проверь адрес доставки.')
    return redirect('users:dashboard')


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerAddress
    form_class = CustomerAddressForm
    template_name = 'users/address_form.html'
    success_url = reverse_lazy('users:dashboard')

    def get_queryset(self):
        return self.request.user.addresses.all()

    def form_valid(self, form):
        messages.success(self.request, 'Адрес обновлен.')
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerAddress
    template_name = 'users/address_confirm_delete.html'
    success_url = reverse_lazy('users:dashboard')

    def get_queryset(self):
        return self.request.user.addresses.all()

    def form_valid(self, form):
        messages.success(self.request, 'Адрес удален.')
        return super().form_valid(form)
