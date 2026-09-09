from decimal import Decimal

from catalog.models import Product
from .forms import CartAddProductForm

CART_SESSION_ID = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(CART_SESSION_ID, {})

    def __iter__(self):
        product_ids = self.cart.keys()
        products = (
            Product.objects.active()
            .filter(id__in=product_ids, category__is_active=True)
            .select_related('category')
            .prefetch_related('images')
        )
        product_map = {str(product.id): product for product in products}

        for product_id, item in list(self.cart.items()):
            product = product_map.get(product_id)
            if product is None:
                self.remove_by_id(product_id)
                continue

            quantity = min(int(item.get('quantity', 0)), product.stock)
            if quantity <= 0:
                self.remove_by_id(product_id)
                continue

            if quantity != item.get('quantity'):
                self.cart[product_id]['quantity'] = quantity
                self.save()

            yield {
                'product': product,
                'quantity': quantity,
                'unit_price': product.price,
                'total_price': product.price * quantity,
                'update_quantity_form': CartAddProductForm(
                    initial={'quantity': quantity, 'override': True},
                    max_quantity=product.stock,
                ),
            }

    def __len__(self):
        return sum(int(item.get('quantity', 0)) for item in self.cart.values())

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product.stock <= 0:
            return 0

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0}

        if override_quantity:
            new_quantity = quantity
        else:
            new_quantity = self.cart[product_id]['quantity'] + quantity

        new_quantity = max(1, min(int(new_quantity), product.stock))
        self.cart[product_id]['quantity'] = new_quantity
        self.save()
        return new_quantity

    def update(self, product, quantity):
        if int(quantity) <= 0:
            self.remove(product)
            return 0
        return self.add(product, quantity=quantity, override_quantity=True)

    def remove(self, product):
        self.remove_by_id(str(product.id))

    def remove_by_id(self, product_id):
        if str(product_id) in self.cart:
            del self.cart[str(product_id)]
            self.save()

    def clear(self):
        if CART_SESSION_ID in self.session:
            del self.session[CART_SESSION_ID]
            self.cart = {}
            self.session.modified = True

    def save(self):
        self.session[CART_SESSION_ID] = self.cart
        self.session.modified = True

    def get_total_price(self):
        total = Decimal('0')
        for item in self:
            total += item['total_price']
        return total
