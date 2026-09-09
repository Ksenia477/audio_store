from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db import transaction


class CustomerAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='пользователь',
        related_name='addresses',
        on_delete=models.CASCADE,
    )
    title = models.CharField('название', max_length=120, default='Основной адрес')
    full_name = models.CharField('получатель', max_length=180)
    phone = models.CharField('телефон', max_length=40)
    city = models.CharField('город', max_length=120)
    street = models.CharField('улица', max_length=180)
    house = models.CharField('дом', max_length=40)
    apartment = models.CharField('квартира/офис', max_length=40, blank=True)
    postal_code = models.CharField('индекс', max_length=20, blank=True)
    comment = models.CharField('комментарий', max_length=240, blank=True)
    is_default = models.BooleanField('адрес по умолчанию', default=True)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлен', auto_now=True)

    class Meta:
        verbose_name = 'адрес покупателя'
        verbose_name_plural = 'адреса покупателей'
        ordering = ['-is_default', '-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='one_default_address_per_user',
            ),
        ]

    def __str__(self):
        return f"{self.title}: {self.city}, {self.street}, {self.house}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_default and self.user_id:
                (
                    CustomerAddress.objects.filter(user=self.user, is_default=True)
                    .exclude(pk=self.pk)
                    .update(is_default=False)
                )
            super().save(*args, **kwargs)
