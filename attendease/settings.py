from pathlib import Path
import os




# ✅ Force DeepFace to use your custom models folder
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ["DEEPFACE_HOME"] = os.path.join(BASE_DIR, "media", "deepface_models")

import os

ALLOWED_HOSTS = ['https://attend-ease-backend.onrender.com]
SECRET_KEY = os.environ.get('SECRET_KEY', '97665b4de43d2bab61ba698612f18347')

AUTH_USER_MODEL = "accounts.CustomUser"
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# LOGIN_REDIRECT_URL = "userdash"
# LOGOUT_REDIRECT_URL = "accounts/login"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-n6p6cpn-(j5r_beb-019^^1zbeo4v8&nyuk21we*3e#=2buyq8'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin', 
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    "django_browser_reload"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
]

ROOT_URLCONF = 'attendease.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "accounts/templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'attendease.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases


import dj_database_url

# ... your existing code ...

# Use dj-database-url to read the DATABASE_URL environment variable
# If the URL is set (i.e., you are in production), use Postgres
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            ssl_require=True
        )
    }
# Otherwise (i.e., you are local), use SQLite
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }



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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"   # where collectstatic will copy everything
STATICFILES_DIRS = [BASE_DIR / "static"] # your development static folder

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

JAZZMIN_SETTINGS = {
    "site_title": "AttendEase Admin",
    "site_header": "AttendEase Admin",
    "site_brand": "AttendEase Admin",
    "site_logo" : "logo.jpg",
    "site_logo_classes": "img-fluid", 
    "site_icon": "logobluenobg.ico",
    "welcome_sign": "Welcome to AttendEase Admin",
    
    "topmenu_links": [
    {"name": "Main Site", "url": "/accounts/home/", "permissions": ["auth.view_user"]},
    ],

    # Optional: add it to the user dropdown menu (top-right corner)
    "usermenu_links": [
        {"name": "Main Site", "url": "/", "icon": "fas fa-home"},
    ],

}

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
print(BASE_DIR)
