"""Project settings for the audio store."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

TRUE_VALUES = {"1", "true", "yes", "on"}
DOTENV_OVERRIDE = (
    os.getenv("DJANGO_DOTENV_OVERRIDE", "True").strip().lower() in TRUE_VALUES
)

load_dotenv(BASE_DIR / ".env", override=DOTENV_OVERRIDE)


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in TRUE_VALUES


def env_int(name, default):
    return int(os.getenv(name, str(default)).strip())


def env_list(*names, default=""):
    raw_value = default
    for name in names:
        value = os.getenv(name)
        if value:
            raw_value = value
            break
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-local-development-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'storages',
    'catalog',
    'cart',
    'users',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_summary',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=env_int("DATABASE_CONN_MAX_AGE", 600),
    )
}
DATABASES['default']['CONN_HEALTH_CHECKS'] = env_bool(
    "DATABASE_CONN_HEALTH_CHECKS",
    True,
)


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

if env_bool("USE_S3"):
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ru-1")
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", "")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False

    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "shop@example.com")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
YOOKASSA_USE_MOCK = env_bool("YOOKASSA_USE_MOCK", True)
YOOKASSA_CURRENCY = os.getenv("YOOKASSA_CURRENCY", "RUB")

CDEK_CLIENT_ID = os.getenv("CDEK_CLIENT_ID", "")
CDEK_CLIENT_SECRET = os.getenv("CDEK_CLIENT_SECRET", "")
CDEK_USE_MOCK = env_bool("CDEK_USE_MOCK", True)
CDEK_BASE_URL = os.getenv("CDEK_BASE_URL", "https://api.edu.cdek.ru/v2")
CDEK_FROM_CITY_CODE = env_int("CDEK_FROM_CITY_CODE", 44)
CDEK_SHIPMENT_POINT = os.getenv("CDEK_SHIPMENT_POINT", "")
CDEK_COURIER_TARIFF_CODE = env_int("CDEK_COURIER_TARIFF_CODE", 136)
CDEK_PICKUP_TARIFF_CODE = env_int("CDEK_PICKUP_TARIFF_CODE", 137)
CDEK_PACKAGE_WEIGHT_GRAMS = env_int("CDEK_PACKAGE_WEIGHT_GRAMS", 1000)
CDEK_PACKAGE_LENGTH_CM = env_int("CDEK_PACKAGE_LENGTH_CM", 20)
CDEK_PACKAGE_WIDTH_CM = env_int("CDEK_PACKAGE_WIDTH_CM", 15)
CDEK_PACKAGE_HEIGHT_CM = env_int("CDEK_PACKAGE_HEIGHT_CM", 10)
CDEK_MOCK_COURIER_PRICE = os.getenv("CDEK_MOCK_COURIER_PRICE", "590.00")
CDEK_MOCK_PICKUP_PRICE = os.getenv("CDEK_MOCK_PICKUP_PRICE", "390.00")

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", False)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    False,
)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
APP_VERSION = os.getenv("APP_VERSION", "local")

INSECURE_SECRET_KEYS = {
    "change-me",
    "django-insecure-local-development-key",
    "replace-with-a-long-random-secret-key-at-least-50-characters",
}

if not DEBUG and (SECRET_KEY in INSECURE_SECRET_KEYS or len(SECRET_KEY) < 50):
    raise ValueError("Set SECRET_KEY before running the project with DEBUG=False.")

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'users:dashboard'
LOGOUT_REDIRECT_URL = 'catalog:product_list'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
