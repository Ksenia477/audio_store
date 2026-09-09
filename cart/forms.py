from django import forms


class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label='Количество',
        widget=forms.NumberInput(attrs={'min': 1}),
    )
    override = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput,
    )

    def __init__(self, *args, max_quantity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_quantity = max_quantity
        if max_quantity is not None:
            self.fields['quantity'].max_value = max_quantity
            self.fields['quantity'].widget.attrs['max'] = max_quantity

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.max_quantity is not None and quantity > self.max_quantity:
            raise forms.ValidationError(
                f'В наличии только {self.max_quantity} шт.',
                code='not_enough_stock',
            )
        return quantity
