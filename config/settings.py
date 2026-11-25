"""Django settings for Eligo (Django 5.2 LTS, SQLite, fully offline)."""
import os
import warnings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- security ---------------------------------------------------------------------------------
_DEV_SECRET = "eligo-dev-only-secret-change-me-in-ELIGO_SECRET_KEY"
SECRET_KEY = os.environ.get("ELIGO_SECRET_KEY", _DEV_SECRET)
DEBUG = os.environ.get("ELIGO_DEBUG", "1") == "1"
if SECRET_KEY == _DEV_SECRET and not DEBUG:
    warnings.warn("ELIGO_SECRET_KEY is not set; using the development secret key.", stacklevel=1)
ALLOWED_HOSTS = os.environ.get("ELIGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False   # templates read the token from the form field, not the cookie
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# --- apps ---------------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "students",
    "internships",
    "assessments",
    "recommendations",
    "adminpanel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "recommendations.context_processors.ai_status",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

# --- auth -----------------------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:home"
LOGOUT_REDIRECT_URL = "accounts:login"

# --- i18n -----------------------------------------------------------------------------------------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- static ---------------------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Eligo ------------------------------------------------------------------------------------------
ELIGO_ARTIFACTS_DIR = BASE_DIR / "artifacts"
#: Grace period (seconds) after an exam deadline in which a submit still counts as on time.
ELIGO_EXAM_GRACE_SECONDS = 10
#: Whether the optional Ollama LLM may be used for skill-gap analysis (falls back automatically).
ELIGO_USE_LLM = os.environ.get("ELIGO_USE_LLM", "1") == "1"
