"""
Django settings for nftmarket project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import os

from pathlib import Path
from django.utils.translation import gettext_lazy as _


ENV = os.getenv('DJANGO_ENV', default='PRODUCTION').upper()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET', default='')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False if ENV == 'PRODUCTION' else True

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'sorl.thumbnail',
    'nftmarket.core'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'nftmarket.core.middleware.ForceDefaultLanguageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'nftmarket.core.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'nftmarket.app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'nftmarket.core.context_processors.settings',
                'nftmarket.core.context_processors.auth',
                'nftmarket.core.context_processors.urltag',
                'nftmarket.core.context_processors.tutorial',
            ],
            # 'libraries': {
            #     'stars': 'nftmarket.core.templatetags.stars'
            # }
        },
    },
]

WSGI_APPLICATION = 'nftmarket.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DJANGO_DB_NAME', default='default'),
        'USER': os.getenv('DJANGO_DB_USER', default='postgres'),
        'PASSWORD': os.getenv('DJANGO_DB_PASSWORD', default='postgres'),
        'HOST': os.getenv('DJANGO_DB_HOST', default='db'),
        'PORT': '5432',
        'AUTOCOMMIT': True
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('uk', _('Ukrainian')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale'
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = 'media/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


APP_NAME = 'Fomo.rip'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/profile/'
LOGOUT_REDIRECT_URL = '/'

DEAL_STATUS_TIMEOUT_MINUTES = 60
DEAL_COMPLETION_TIMEOUT_MINUTES = 180
MAX_UPLOAD_SIZE = 2 * 1024 * 1024

MIN_PRICE = os.getenv('FOMORIP_MIN_PRICE', 1)
FEE_PERCENT = os.getenv('FOMORIP_FEE_PERCENT', 1)

PROJECT_PATH = Path('.')
TEMPLATES_PATH = PROJECT_PATH / 'templates'
TEMPLATES[0]['DIRS'] = [TEMPLATES_PATH]

# STATICFILES_DIRS = [
#     PROJECT_PATH / 'static'
# ]

STATIC_ROOT = PROJECT_PATH / 'static'
MEDIA_ROOT = PROJECT_PATH / 'media'

NETWORKS = {
    'bnb': {
        'url': 'https://bsc-dataseed.binance.org',
        'chain_id': 56,
        'escrow_addr': os.getenv('FOMORIP_BNB_ESCROW_ADDR'),
        'token_name': 'busd',
        'token_addr': '0xe9e7cea3dedca5984780bafc599bd69add087d56',
        'token_decimals': 18,
        'gaz': os.getenv('FOMORIP_BNB_GAZ_LIMIT', default=1000000),
        'gaz_price': os.getenv('FOMORIP_BNB_GAZ_PRICE', default=10000000000)
    },
    'arbitrum': {
        'url': 'https://arb1.arbitrum.io/rpc',
        'chain_id': 42161,
        'escrow_addr': os.getenv('FOMORIP_ARBITRUM_ESCROW_ADDR'),
        'token_name': 'usdc',
        'token_addr': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
        'token_decimals': 6,
        'gaz': os.getenv('FOMORIP_ARBITRUM_GAZ_LIMIT', default=1000000),
        'gaz_price': os.getenv('FOMORIP_ARBITRUM_GAZ_PRICE', default=100000000)
    },
    'optimism': {
        'url': 'https://mainnet.optimism.io',
        'chain_id': 10,
        'escrow_addr': os.getenv('FOMORIP_OPTIMIZM_ESCROW_ADDR'),
        'token_name': 'usdc',
        'token_addr': '0x7f5c764cbc14f9669b88837ca1490cca17c31607',
        'token_decimals': 6,
        'gaz': os.getenv('FOMORIP_OPTIMIZM_GAZ_LIMIT', default=2000000),
        'gaz_price': os.getenv('FOMORIP_OPTIMIZM_GAZ_PRICE', default=1000000)
    }
}
