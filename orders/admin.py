from django.contrib import admin

from .models import Order, OrderItem, Payment, Shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'product_name', 'product_sku', 'unit_price', 'quantity')


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = (
        'provider',
        'provider_payment_id',
        'status',
        'amount',
        'currency',
        'confirmation_url',
        'paid_at',
    )
    readonly_fields = ('paid_at',)


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0
    fields = (
        'provider',
        'delivery_method',
        'status',
        'tariff_code',
        'delivery_price',
        'period_min',
        'period_max',
        'to_city',
        'to_city_code',
        'recipient_address',
        'delivery_point',
        'cdek_uuid',
        'cdek_number',
        'tracking_number',
        'registered_at',
    )
    readonly_fields = ('registered_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'email',
        'phone',
        'status',
        'payment_status',
        'shipment_status',
        'total_price',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'shipment_status', 'created_at')
    search_fields = ('id', 'email', 'phone', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (OrderItemInline, ShipmentInline, PaymentInline)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'unit_price', 'quantity')
    search_fields = ('order__id', 'product_name', 'product_sku')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'provider', 'provider_payment_id', 'status', 'amount', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('order__id', 'provider_payment_id')
    readonly_fields = ('idempotency_key', 'raw_response', 'created_at', 'updated_at', 'paid_at')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'provider',
        'delivery_method',
        'status',
        'delivery_price',
        'tracking_number',
        'updated_at',
    )
    list_filter = ('provider', 'delivery_method', 'status')
    search_fields = ('order__id', 'cdek_uuid', 'cdek_number', 'tracking_number', 'to_city')
    readonly_fields = ('raw_request', 'raw_response', 'created_at', 'updated_at', 'registered_at')
