from decimal import Decimal
from pathlib import Path

from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.text import slugify


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Category(models.Model):
    name = models.CharField('название', max_length=160)
    slug = models.SlugField('slug', max_length=180, unique=True)
    description = models.TextField('описание', blank=True)
    sort_order = models.PositiveIntegerField('порядок', default=0)
    is_active = models.BooleanField('активна', default=True)
    created_at = models.DateTimeField('создана', auto_now_add=True)
    updated_at = models.DateTimeField('обновлена', auto_now=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category', kwargs={'slug': self.slug})


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        verbose_name='категория',
        related_name='products',
        on_delete=models.PROTECT,
    )
    name = models.CharField('название', max_length=220)
    slug = models.SlugField('slug', max_length=240, unique=True)
    sku = models.CharField('артикул', max_length=80, blank=True, null=True, unique=True)
    barcode = models.CharField('штрихкод', max_length=80, blank=True)
    ozon_url = models.URLField('ссылка на Ozon', max_length=500, blank=True)
    short_description = models.CharField('краткое описание', max_length=280, blank=True)
    description = models.TextField('описание', blank=True)
    price = models.DecimalField('цена', max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        'старая цена',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    stock = models.PositiveIntegerField('остаток', default=0)
    is_active = models.BooleanField('активен', default=True)
    is_featured = models.BooleanField('на главной', default=False)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлен', auto_now=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'
        ordering = ['category__sort_order', 'category__name', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def main_image(self):
        main = self.images.filter(is_main=True).first()
        return main or self.images.first()

    @property
    def has_discount(self):
        return self.old_price and self.old_price > self.price

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        discount = (self.old_price - self.price) / self.old_price * Decimal('100')
        return int(discount.quantize(Decimal('1')))


def product_image_upload_to(instance, filename):
    product = instance.product
    folder_source = product.sku or product.slug or f"product-{product.pk or 'new'}"
    folder = slugify(folder_source)[:60] or f"product-{product.pk or 'new'}"
    original = Path(filename)
    stem = slugify(original.stem)[:70] or 'image'
    suffix = original.suffix.lower()[:10]
    return f"products/{folder}/{stem}-{get_random_string(6)}{suffix}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name='товар',
        related_name='images',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        'изображение',
        upload_to=product_image_upload_to,
        max_length=255,
    )
    alt_text = models.CharField('alt-текст', max_length=220, blank=True)
    sort_order = models.PositiveIntegerField('порядок', default=0)
    is_main = models.BooleanField('главное изображение', default=False)

    class Meta:
        verbose_name = 'изображение товара'
        verbose_name_plural = 'изображения товаров'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.alt_text or f"Изображение: {self.product}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name='товар',
        related_name='specifications',
        on_delete=models.CASCADE,
    )
    name = models.CharField('название', max_length=160)
    value = models.CharField('значение', max_length=260)
    sort_order = models.PositiveIntegerField('порядок', default=0)

    class Meta:
        verbose_name = 'характеристика'
        verbose_name_plural = 'характеристики'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name}: {self.value}"
