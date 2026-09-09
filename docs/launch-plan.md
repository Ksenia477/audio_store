# План запуска WSTER

Цель: довести магазин до рабочего состояния с оплатой, доставкой СДЭК и доменом
`wster.ru`.

## 1. Проверить текущий магазин

- Пройти тестовый заказ в mock-режиме: каталог -> корзина -> оформление -> оплата -> завершение.
- Проверить, что остатки товаров корректно уменьшаются после заказа.
- Проверить карточки товаров, фото, цены, наличие, ссылки на Ozon и внутренние штрихкоды.
- Перед деплоем сохранить резервную копию локальной базы и папки `media/`.

## 2. Подключить ЮKassa в тестовом режиме

Что уже есть в проекте:

- создание платежа через YooKassa SDK;
- redirect-подтверждение оплаты;
- обработчик возврата покупателя;
- webhook endpoint `/orders/webhooks/yookassa/`;
- mock-режим для локальных проверок.

Что нужно получить в кабинете ЮKassa:

- тестовый `shopId`;
- тестовый секретный ключ;
- список подключенных способов оплаты;
- решение по чекам/онлайн-кассе перед боевыми платежами.

Переменные для теста:

```env
YOOKASSA_USE_MOCK=False
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
YOOKASSA_CURRENCY=RUB
```

Webhook после публикации сайта:

```text
https://wster.ru/orders/webhooks/yookassa/
```

## 3. Подключить СДЭК в тестовом режиме

Что уже есть в проекте:

- расчет доставки через `/calculator/tariff`;
- регистрация заказа через `/orders`;
- синхронизация статуса отправления;
- mock-режим для локальной разработки.

Что нужно получить/уточнить:

- `client_id` и `client_secret` API СДЭК;
- город отправления СДЭК;
- код склада/ПВЗ отправления `CDEK_SHIPMENT_POINT`;
- реальные габариты и вес посылки;
- тарифы для курьера и ПВЗ;
- нужен ли удобный выбор ПВЗ на сайте вместо ручного поля кода ПВЗ.

Переменные для теста:

```env
CDEK_USE_MOCK=False
CDEK_CLIENT_ID=...
CDEK_CLIENT_SECRET=...
CDEK_BASE_URL=https://api.edu.cdek.ru/v2
CDEK_FROM_CITY_CODE=44
CDEK_SHIPMENT_POINT=...
CDEK_COURIER_TARIFF_CODE=136
CDEK_PICKUP_TARIFF_CODE=137
CDEK_PACKAGE_WEIGHT_GRAMS=1000
CDEK_PACKAGE_LENGTH_CM=20
CDEK_PACKAGE_WIDTH_CM=15
CDEK_PACKAGE_HEIGHT_CM=10
```

## 4. Подготовить production

Минимум для запуска:

- GitHub/GitLab-репозиторий с актуальным кодом;
- production PostgreSQL;
- S3-совместимое хранилище для фото товаров;
- секретный `SECRET_KEY`;
- SMTP-почта для писем магазина;
- `DEBUG=False`;
- HTTPS.

Production-переменные лежат в `.env.production.example`.

## 5. Выложить сайт на `wster.ru`

Порядок:

1. Создать приложение в Timeweb Cloud App Platform из репозитория.
2. Указать build command: `bash deploy/timeweb-build.sh`.
3. Указать start command: `bash deploy/timeweb-start.sh`.
4. Подключить PostgreSQL и заполнить `DATABASE_URL`.
5. Заполнить production env-переменные.
6. Подключить домены `wster.ru` и `www.wster.ru`.
7. У регистратора домена прописать DNS-записи, которые покажет Timeweb.
8. Дождаться SSL-сертификата.
9. Проверить `https://wster.ru/healthz/`.

## 6. Переключить тестовые интеграции на боевые

После успешных тестов:

```env
YOOKASSA_USE_MOCK=False
CDEK_USE_MOCK=False
CDEK_BASE_URL=https://api.cdek.ru/v2
```

И заменить тестовые ключи ЮKassa/СДЭК на боевые.

## Следующий лучший шаг

Сначала подключить ЮKassa в тестовом режиме. Это самый короткий путь проверить,
что деньги, статусы заказа и webhook работают до настройки домена и боевых
ключей.
