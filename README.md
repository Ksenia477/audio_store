# WSTER

Django-магазин аудиотехники. Текущая версия содержит каталог, карточки товаров,
поиск, категории, загрузку фотографий, Django Admin, корзину на Django Session,
регистрацию, личный кабинет, адреса, историю заказов, оформление заказа и
тестовую оплату через ЮKassa/mock и доставку СДЭК/mock.

## Локальный запуск

```bash
source .venv312/bin/activate
python manage.py migrate
python manage.py seed_demo_catalog
python manage.py createsuperuser
python manage.py runserver
```

Сайт откроется на `http://127.0.0.1:8000/`, админка — на
`http://127.0.0.1:8000/admin/`.

## Настройки окружения

```bash
cp .env.example .env
```

Для локальной разработки можно оставить SQLite. Для managed PostgreSQL позже
достаточно задать `DATABASE_URL`.

## Production-запуск

```bash
bash deploy/timeweb-build.sh
bash deploy/timeweb-start.sh
```

Для deployment нужно задать `DEBUG=False`, надежный `SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` и
HTTPS-настройки. Пошаговый план запуска лежит в `docs/launch-plan.md`.

Healthcheck проекта:

```text
/healthz/
```

## Deployment 0.7: Timeweb Cloud, домен, HTTPS

Если домен уже куплен, порядок такой:

1. Залить проект в GitHub или GitLab.
2. Создать приложение в Timeweb Cloud App Platform из репозитория.
3. Указать build command:

```bash
bash deploy/timeweb-build.sh
```

4. Указать start command:

```bash
bash deploy/timeweb-start.sh
```

5. Добавить managed PostgreSQL и передать строку подключения в `DATABASE_URL`.
6. В переменных окружения приложения заполнить значения по примеру
   `.env.production.example`.
7. Подключить домен в настройках приложения, затем у регистратора домена
   прописать DNS-записи, которые покажет Timeweb.
8. Включить SSL/HTTPS для домена.
9. Проверить `https://wster.ru/healthz/`.

Минимальный набор production-переменных:

```env
DEBUG=False
DJANGO_DOTENV_OVERRIDE=False
SECRET_KEY=replace-with-a-long-random-secret-key-at-least-50-characters
DJANGO_ALLOWED_HOSTS=wster.ru,www.wster.ru
DJANGO_CSRF_TRUSTED_ORIGINS=https://wster.ru,https://www.wster.ru
DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DB_NAME
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=0
```

`SECURE_HSTS_SECONDS` лучше оставить `0` до тех пор, пока HTTPS стабильно
работает на основном домене и `www`. После проверки можно поднять до `31536000`.

Для загружаемых фотографий товаров на production лучше включить S3-совместимое
хранилище:

```env
USE_S3=True
AWS_STORAGE_BUCKET_NAME=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_ENDPOINT_URL=...
AWS_S3_CUSTOM_DOMAIN=...
```

На Timeweb порт приложения приходит через переменную `PORT`; стартовый скрипт
уже использует ее автоматически.

## ЮKassa

По умолчанию включен локальный mock-режим:

```env
YOOKASSA_USE_MOCK=True
```

Для тестовой ЮKassa в кабинете ЮKassa нужно взять тестовые `shopId` и секретный
ключ, затем задать:

```env
YOOKASSA_USE_MOCK=False
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
```

Webhook endpoint для уведомлений:

```text
/orders/webhooks/yookassa/
```

## СДЭК

По умолчанию включен локальный mock-режим:

```env
CDEK_USE_MOCK=True
```

Для тестового API СДЭК нужно задать:

```env
CDEK_USE_MOCK=False
CDEK_CLIENT_ID=...
CDEK_CLIENT_SECRET=...
CDEK_BASE_URL=https://api.edu.cdek.ru/v2
CDEK_FROM_CITY_CODE=44
CDEK_SHIPMENT_POINT=...
```

В checkout можно выбрать курьерскую доставку или пункт выдачи. В реальном режиме
для более точного расчета можно передавать `Код города СДЭК` и `Код ПВЗ СДЭК`.

## Версии разработки

- `0.1`: каталог, товары, фотографии, характеристики, поиск, Django Admin.
- `0.2`: корзина на Django Session.
- `0.3`: регистрация, личный кабинет, адреса, история заказов.
- `0.4`: оформление заказа без оплаты.
- `0.5`: тестовая интеграция ЮKassa и локальный mock-режим.
- `0.6`: доставка СДЭК и локальный mock-режим.
- `0.7`: deployment, домен, HTTPS.
