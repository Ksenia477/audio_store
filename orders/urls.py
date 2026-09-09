from django.urls import path

from . import views
from .views import OrderDetailView, OrderListView

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('complete/<int:pk>/', views.order_complete, name='complete'),
    path('pay/<int:pk>/', views.start_payment, name='start_payment'),
    path('shipments/<int:pk>/sync/', views.sync_shipment, name='sync_shipment'),
    path('payment-return/<int:pk>/', views.payment_return, name='payment_return'),
    path('mock-payment/<str:provider_payment_id>/', views.mock_payment, name='mock_payment'),
    path('webhooks/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
    path('', OrderListView.as_view(), name='list'),
    path('<int:pk>/', OrderDetailView.as_view(), name='detail'),
]
