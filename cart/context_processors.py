from .cart import Cart


def cart_summary(request):
    return {'cart_summary': Cart(request)}
