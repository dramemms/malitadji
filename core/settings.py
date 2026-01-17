from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
FIREBASE_SERVICE_ACCOUNT_FILE = BASE_DIR / "core" / "firebase_service_account.json"

# =========================
# SECURITY
# =========================
SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-default-key-change-me")
DEBUG = True  # passe à False en prod

ALLOWED_HOSTS = [
    "malitadji.onrender.com",
    "malitadji.com",
    "www.malitadji.com",
    "127.0.0.1",
    "localhost",
    "192.168.88.206",  # LAN (téléphone / autres postes)
]

# =========================
# APPLICATIONS
# =========================
INSTALLED_APPS = [
    # CORS
    "corsheaders",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Tes apps
    
    "manager",
     "stations.apps.StationsConfig",
]

# =========================
# MIDDLEWARE (ordre important)
# =========================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # toujours en haut
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =========================
# CORS / CSRF
# =========================
# ✅ Recommandé : origins explicites
# (Ne pas utiliser CORS_ALLOW_ALL_ORIGINS=True avec CORS_ALLOW_CREDENTIALS=True)
CORS_ALLOW_ALL_ORIGINS = True

# Origines du FRONT (Flutter Web / Vite dev server)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:13691",
    "http://127.0.0.1:13691",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:50827",
    "http://127.0.0.1:50827",
]

# Si tu utilises cookies/sessions (sinon tu peux mettre False)
CORS_ALLOW_CREDENTIALS = True

# Autoriser l’accès LAN en dev (Chrome Private Network Access)
CORS_ALLOW_PRIVATE_NETWORK = True

# Si tu utilises SessionAuth/CSRF (souvent utile en admin)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:13691",
    "http://127.0.0.1:13691",
    "http://localhost:50827",
    "http://127.0.0.1:50827",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Optionnel: headers autorisés (utile si tu envoies Authorization)
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
]

# =========================
# URL / TEMPLATES
# =========================
ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# =========================
# DATABASE
# =========================
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
        ssl_require=False,
    )
}

# =========================
# PASSWORDS
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# I18N
# =========================
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Bamako"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC FILES
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =========================
# DEFAULT PRIMARY KEY
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
