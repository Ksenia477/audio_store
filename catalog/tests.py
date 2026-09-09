import base64
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse

from .admin import ProductAdmin
from .barcodes import BarcodeValueError, barcode_svg_data_uri
from .models import Category, Product, ProductImage, product_image_upload_to


class CatalogViewsTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Микрофоны', slug='microphones')
        self.product = Product.objects.create(
            category=self.category,
            name='Fifine K688',
            slug='fifine-k688',
            sku='MIC-001',
            short_description='Динамический USB/XLR микрофон',
            price=Decimal('8990.00'),
            stock=3,
        )

    def test_product_list_shows_active_product(self):
        response = self.client.get(reverse('catalog:product_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_product_detail_shows_product(self):
        response = self.client.get(self.product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_product_detail_shows_ozon_link_but_not_barcode(self):
        self.product.ozon_url = 'https://www.ozon.ru/product/example-123/'
        self.product.barcode = '4601234567890'
        self.product.save(update_fields=['ozon_url', 'barcode'])

        response = self.client.get(self.product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Смотреть на Ozon')
        self.assertContains(response, self.product.ozon_url)
        self.assertNotContains(response, self.product.barcode)

    def test_search_filters_products(self):
        response = self.client.get(reverse('catalog:product_list'), {'q': 'USB'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)


class ProductImageUploadPathTests(TestCase):
    def test_image_upload_path_uses_short_product_identifier(self):
        category = Category.objects.create(name='Колонки', slug='speakers')
        product = Product.objects.create(
            category=category,
            name='Беспроводная колонка-машина WS-1967 Ford Mustang GT Bluetooth, синяя',
            slug='besprovodnaya-kolonka-mashina-ws-1967-ford-mustang-gt-bluetooth-sinyaya-1396828254',
            sku='OZON-1396828254',
            price=Decimal('2000.00'),
            stock=10,
        )

        upload_path = product_image_upload_to(
            ProductImage(product=product),
            'image_A2Uvogk.png',
        )

        self.assertTrue(upload_path.startswith('products/ozon-1396828254/'))
        self.assertLess(len(upload_path), 100)


class BarcodeTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Колонки', slug='speakers')
        self.product = Product.objects.create(
            category=self.category,
            name='WS-1967',
            slug='ws-1967',
            sku='OZON-1396829540',
            barcode='4601234567890',
            price=Decimal('2000.00'),
            stock=10,
        )

    def test_barcode_svg_data_uri_contains_readable_value(self):
        data_uri = barcode_svg_data_uri(self.product.barcode)
        prefix, encoded = data_uri.split(',', 1)
        svg = base64.b64decode(encoded).decode('utf-8')

        self.assertEqual(prefix, 'data:image/svg+xml;base64')
        self.assertIn('<svg', svg)
        self.assertIn('<rect', svg)
        self.assertIn(self.product.barcode, svg)

    def test_barcode_svg_rejects_non_ascii_values(self):
        with self.assertRaises(BarcodeValueError):
            barcode_svg_data_uri('штрихкод')

    def test_admin_barcode_preview_renders_image(self):
        product_admin = ProductAdmin(Product, AdminSite())

        html = str(product_admin.barcode_preview(self.product))

        self.assertIn('data:image/svg+xml;base64', html)
        self.assertIn(self.product.barcode, html)
