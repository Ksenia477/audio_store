from django.contrib import admin
from django.utils.html import format_html

from .barcodes import BarcodeValueError, barcode_svg_data_uri
from .models import Category, Product, ProductImage, ProductSpecification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'sort_order', 'is_main')


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    fields = ('name', 'value', 'sort_order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'sku',
        'barcode',
        'barcode_preview_small',
        'price',
        'stock',
        'is_active',
        'is_featured',
        'ozon_admin_link',
        'updated_at',
    )
    list_editable = ('price', 'stock', 'is_active', 'is_featured')
    list_filter = ('category', 'is_active', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('barcode_preview', 'created_at', 'updated_at')
    search_fields = ('name', 'sku', 'barcode', 'short_description', 'description')
    fieldsets = (
        (
            'Основное',
            {
                'fields': (
                    'category',
                    'name',
                    'slug',
                    'sku',
                    'short_description',
                    'description',
                )
            },
        ),
        (
            'Продажи',
            {
                'fields': (
                    'price',
                    'old_price',
                    'stock',
                    'is_active',
                    'is_featured',
                )
            },
        ),
        (
            'Внутренние данные',
            {
                'fields': ('barcode', 'barcode_preview', 'ozon_url'),
                'description': 'Штрихкод используется только внутри админки и не показывается покупателям.',
            },
        ),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )
    inlines = (ProductImageInline, ProductSpecificationInline)

    @admin.display(description='Ozon')
    def ozon_admin_link(self, obj):
        if not obj.ozon_url:
            return '-'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Открыть</a>',
            obj.ozon_url,
        )

    @admin.display(description='Картинка штрихкода')
    def barcode_preview_small(self, obj):
        return self._barcode_image(obj, module_width=1, bar_height=34, font_size=9)

    @admin.display(description='Изображение штрихкода')
    def barcode_preview(self, obj):
        if not obj or not obj.barcode:
            return 'Добавьте номер штрихкода и сохраните товар.'
        return self._barcode_image(obj, module_width=2, bar_height=72, font_size=14)

    def _barcode_image(self, obj, **kwargs):
        if not obj or not obj.barcode:
            return '-'
        try:
            data_uri = barcode_svg_data_uri(obj.barcode, **kwargs)
        except BarcodeValueError as error:
            return format_html(
                '<span style="color: #ba2121;">{}</span>',
                str(error),
            )
        return format_html(
            '<div style="display: inline-grid; gap: 6px; max-width: 100%;">'
            '<img src="{}" alt="Штрихкод {}" '
            'style="max-width: 360px; height: auto; background: #fff; '
            'border: 1px solid #ddd; padding: 8px;">'
            '<code>{}</code>'
            '</div>',
            data_uri,
            obj.barcode,
            obj.barcode,
        )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'sort_order', 'is_main', 'alt_text')
    list_editable = ('sort_order', 'is_main')
    list_filter = ('is_main',)
    search_fields = ('product__name', 'alt_text')


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'value', 'sort_order')
    list_editable = ('sort_order',)
    search_fields = ('product__name', 'name', 'value')
