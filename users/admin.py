from django.contrib import admin

from .models import CustomerAddress


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'city', 'phone', 'is_default', 'updated_at')
    list_filter = ('is_default', 'city')
    search_fields = ('user__username', 'user__email', 'full_name', 'phone', 'city', 'street')
    readonly_fields = ('created_at', 'updated_at')
