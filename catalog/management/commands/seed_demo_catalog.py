from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Category, Product, ProductSpecification


class Command(BaseCommand):
    help = 'Creates demo categories and products for local development.'

    def handle(self, *args, **options):
        microphones, _ = Category.objects.update_or_create(
            slug='microphones',
            defaults={
                'name': 'Микрофоны',
                'description': 'USB, XLR и гибридные микрофоны для записи голоса.',
                'sort_order': 10,
                'is_active': True,
            },
        )
        accessories, _ = Category.objects.update_or_create(
            slug='accessories',
            defaults={
                'name': 'Аксессуары',
                'description': 'Кабели, стойки, поп-фильтры и крепления.',
                'sort_order': 20,
                'is_active': True,
            },
        )

        products = [
            {
                'category': microphones,
                'slug': 'fifine-k688',
                'name': 'Fifine K688',
                'sku': 'MIC-001',
                'short_description': 'Динамический USB/XLR микрофон для подкастов и стриминга.',
                'description': 'Подходит для домашней студии, разговорного контента и прямых эфиров.',
                'price': Decimal('8990.00'),
                'old_price': Decimal('9990.00'),
                'stock': 6,
                'specs': {
                    'Подключение': 'USB-C / XLR',
                    'Тип': 'Динамический',
                    'Диаграмма': 'Кардиоидная',
                },
            },
            {
                'category': microphones,
                'slug': 'maono-pd200x',
                'name': 'Maono PD200X',
                'sku': 'MIC-002',
                'short_description': 'USB/XLR микрофон с RGB-подсветкой и управлением громкостью.',
                'description': 'Хороший вариант для стрима, звонков, озвучки и первого сетапа.',
                'price': Decimal('7490.00'),
                'old_price': None,
                'stock': 4,
                'specs': {
                    'Подключение': 'USB-C / XLR',
                    'Тип': 'Динамический',
                    'Особенность': 'RGB-подсветка',
                },
            },
            {
                'category': accessories,
                'slug': 'xlr-cable-3m',
                'name': 'XLR-кабель 3 м',
                'sku': 'ACC-001',
                'short_description': 'Балансный кабель для микрофонов и аудиоинтерфейсов.',
                'description': 'Длина 3 метра, надежные металлические коннекторы.',
                'price': Decimal('1290.00'),
                'old_price': None,
                'stock': 12,
                'specs': {
                    'Длина': '3 м',
                    'Разъемы': 'XLR female / XLR male',
                    'Тип': 'Балансный',
                },
            },
        ]

        for item in products:
            specs = item.pop('specs')
            product, _ = Product.objects.update_or_create(
                slug=item['slug'],
                defaults={**item, 'is_active': True},
            )
            for index, (name, value) in enumerate(specs.items(), start=1):
                ProductSpecification.objects.update_or_create(
                    product=product,
                    name=name,
                    defaults={'value': value, 'sort_order': index},
                )

        self.stdout.write(self.style.SUCCESS('Demo catalog is ready.'))
