import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalog.models import Category, Product, ProductSpecification


NAMESPACE = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
DEFAULT_FILE = Path('data/ozon_products_draft.xlsx')

CYRILLIC_MAP = {
    'а': 'a',
    'б': 'b',
    'в': 'v',
    'г': 'g',
    'д': 'd',
    'е': 'e',
    'ё': 'e',
    'ж': 'zh',
    'з': 'z',
    'и': 'i',
    'й': 'y',
    'к': 'k',
    'л': 'l',
    'м': 'm',
    'н': 'n',
    'о': 'o',
    'п': 'p',
    'р': 'r',
    'с': 's',
    'т': 't',
    'у': 'u',
    'ф': 'f',
    'х': 'h',
    'ц': 'c',
    'ч': 'ch',
    'ш': 'sh',
    'щ': 'sch',
    'ъ': '',
    'ы': 'y',
    'ь': '',
    'э': 'e',
    'ю': 'yu',
    'я': 'ya',
}


@dataclass
class ImportSummary:
    categories_created: int = 0
    products_created: int = 0
    products_updated: int = 0
    specs_created: int = 0
    specs_updated: int = 0
    rows_skipped: int = 0


def transliterate(value):
    result = []
    for char in value.lower():
        result.append(CYRILLIC_MAP.get(char, char))
    return ''.join(result)


def make_slug(value, fallback):
    slug = slugify(transliterate(value))[:220]
    return slug or fallback


def unique_slug(model, base_slug, current_pk=None, max_length=240):
    slug = base_slug[:max_length]
    suffix = 2
    queryset = model.objects.filter(slug=slug)
    if current_pk:
        queryset = queryset.exclude(pk=current_pk)
    while queryset.exists():
        suffix_text = f'-{suffix}'
        slug = f'{base_slug[: max_length - len(suffix_text)]}{suffix_text}'
        queryset = model.objects.filter(slug=slug)
        if current_pk:
            queryset = queryset.exclude(pk=current_pk)
        suffix += 1
    return slug


def column_number(cell_reference):
    letters = re.match(r'([A-Z]+)', cell_reference).group(1)
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter) - 64
    return number


def read_shared_strings(archive):
    try:
        root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    return [
        ''.join(text.text or '' for text in item.findall('.//m:t', NAMESPACE))
        for item in root.findall('m:si', NAMESPACE)
    ]


def read_xlsx_rows(path):
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        root = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))

    rows = []
    for row in root.findall('.//m:sheetData/m:row', NAMESPACE):
        values = {}
        for cell in row.findall('m:c', NAMESPACE):
            index = column_number(cell.attrib['r'])
            cell_type = cell.attrib.get('t')
            value = cell.find('m:v', NAMESPACE)

            if cell_type == 's' and value is not None:
                text = shared_strings[int(value.text)]
            elif cell_type == 'inlineStr':
                text = ''.join(
                    item.text or ''
                    for item in cell.findall('.//m:t', NAMESPACE)
                )
            elif value is not None:
                text = value.text or ''
            else:
                text = ''

            values[index] = str(text).strip()

        if values:
            rows.append([values.get(index, '') for index in range(1, max(values) + 1)])

    if not rows:
        raise CommandError('Excel file is empty.')
    return rows


def get_cell(row, headers, name):
    try:
        index = headers.index(name)
    except ValueError as error:
        raise CommandError(f'Missing required column: {name}') from error
    if index >= len(row):
        return ''
    return row[index].strip()


def get_optional_cell(row, headers, name):
    try:
        return get_cell(row, headers, name)
    except CommandError:
        return ''


def parse_decimal(value, default=None):
    if not value:
        return default
    cleaned = (
        value.replace('\xa0', '')
        .replace(' ', '')
        .replace('₽', '')
        .replace('руб.', '')
        .replace('руб', '')
        .replace(',', '.')
    )
    try:
        return Decimal(cleaned).quantize(Decimal('0.01'))
    except InvalidOperation as error:
        raise CommandError(f'Invalid decimal value: {value}') from error


def parse_int(value, default=0):
    if not value:
        return default
    try:
        return int(Decimal(value.replace(',', '.')))
    except InvalidOperation as error:
        raise CommandError(f'Invalid integer value: {value}') from error


def parse_bool(value, default=False):
    if not value:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'да', 'д'}


def parse_specs(value):
    specs = []
    for index, item in enumerate(value.split(';'), start=1):
        if ':' not in item:
            continue
        name, spec_value = item.split(':', 1)
        name = name.strip()
        spec_value = spec_value.strip()
        if name and spec_value:
            specs.append((index, name, spec_value))
    return specs


class Command(BaseCommand):
    help = 'Imports catalog products from the prepared Excel file.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(DEFAULT_FILE),
            help='Path to the Excel file.',
        )
        parser.add_argument(
            '--default-price',
            default='2000',
            help='Price for rows with an empty price cell.',
        )
        parser.add_argument(
            '--default-stock',
            default='10',
            help='Stock for rows with an empty stock cell.',
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Make imported products visible in the catalog.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate the file without saving data.',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        if not file_path.exists():
            raise CommandError(f'File does not exist: {file_path}')

        default_price = parse_decimal(options['default_price'])
        default_stock = parse_int(options['default_stock'])
        rows = read_xlsx_rows(file_path)
        headers = rows[0]
        data_rows = rows[1:]

        summary = ImportSummary()
        category_cache = {}

        if options['dry_run']:
            self.stdout.write(f'Validated rows: {len(data_rows)}')
            return

        with transaction.atomic():
            for row in data_rows:
                if not any(row):
                    summary.rows_skipped += 1
                    continue

                category_name = get_cell(row, headers, 'Категория')
                product_name = get_cell(row, headers, 'Название товара')
                sku = get_cell(row, headers, 'Артикул / SKU')
                ozon_id = get_cell(row, headers, 'Ozon ID')

                if not category_name or not product_name:
                    summary.rows_skipped += 1
                    continue

                if not sku:
                    sku = f'OZON-{ozon_id}' if ozon_id else make_slug(product_name, 'product')

                category = category_cache.get(category_name)
                if not category:
                    category_slug = unique_slug(
                        Category,
                        make_slug(category_name, 'category'),
                        max_length=180,
                    )
                    category, created = Category.objects.get_or_create(
                        slug=category_slug,
                        defaults={
                            'name': category_name,
                            'description': '',
                            'sort_order': 100 + len(category_cache) * 10,
                            'is_active': True,
                        },
                    )
                    if created:
                        summary.categories_created += 1
                    category_cache[category_name] = category

                product = Product.objects.filter(sku=sku).first()
                base_slug = make_slug(f'{product_name}-{ozon_id or sku}', sku.lower())
                product_slug = product.slug if product else unique_slug(Product, base_slug)
                price = parse_decimal(get_cell(row, headers, 'Цена'), default=default_price)
                stock = parse_int(get_cell(row, headers, 'Остаток'), default=default_stock)
                old_price = parse_decimal(get_cell(row, headers, 'Старая цена'), default=None)
                is_active = (
                    True
                    if options['activate']
                    else parse_bool(get_cell(row, headers, 'Активен'), default=False)
                )

                defaults = {
                    'category': category,
                    'name': product_name,
                    'slug': product_slug,
                    'barcode': get_optional_cell(row, headers, 'Штрихкод'),
                    'ozon_url': get_optional_cell(row, headers, 'Ссылка на Ozon'),
                    'short_description': get_cell(row, headers, 'Краткое описание'),
                    'description': get_cell(row, headers, 'Полное описание'),
                    'price': price,
                    'old_price': old_price,
                    'stock': stock,
                    'is_featured': parse_bool(get_cell(row, headers, 'На главную')),
                    'is_active': is_active,
                }

                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults=defaults,
                )
                if created:
                    summary.products_created += 1
                else:
                    summary.products_updated += 1

                ProductSpecification.objects.filter(product=product).delete()
                for sort_order, name, value in parse_specs(
                    get_cell(row, headers, 'Характеристики')
                ):
                    ProductSpecification.objects.create(
                        product=product,
                        name=name,
                        value=value,
                        sort_order=sort_order,
                    )
                    summary.specs_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Imported products: '
                f'{summary.products_created} created, '
                f'{summary.products_updated} updated, '
                f'{summary.categories_created} categories created, '
                f'{summary.specs_created} specifications created, '
                f'{summary.rows_skipped} rows skipped.'
            )
        )
