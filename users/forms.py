from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import CustomerAddress

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(label='Имя', max_length=150, required=False)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label='Email')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        exists = User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists()
        if exists:
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = (
            'title',
            'full_name',
            'phone',
            'city',
            'street',
            'house',
            'apartment',
            'postal_code',
            'comment',
            'is_default',
        )
