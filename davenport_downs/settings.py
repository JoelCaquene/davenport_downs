"""
Django settings for davenport_downs project.
"""

from pathlib import Path
import os
import dj_database_url
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# ======================================================================
# CONFIGURAÇÃO DOS HOSTS PERMITIDOS (CORRIGIDO PARA O RENDER.COM)
# ======================================================================
# 1. Pega a string de hosts (ex: "host1, host2, host3")
hosts_string = config('ALLOWED_HOSTS', default='')

# 2. Divide a string pela vírgula e usa list comprehension para remover espaços em branco de cada host
# Isso garante que a lista de hosts fique limpa (ex: ['host1', 'host2', 'host3'])
ALLOWED_HOSTS = [host.strip() for host in hosts_string.split(',') if host.strip()]


# Adiciona o hostname do Render dinamicamente se não estiver em DEBUG
if not DEBUG:
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RENDER_EXTERNAL_HOSTNAME:
        # Garante que o domínio principal do Render seja incluído
        if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
        
        # Adiciona o domínio base do Render para que todos os subdomínios funcionem
        # Nota: Normalmente, apenas o sufixo '.onrender.com' é suficiente, mas vamos manter
        # a lógica original, garantindo que o Render Hostname (davenport-downs.onrender.com)
        # já está coberto pela variável de ambiente ALLOWED_HOSTS
        pass 

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # WhiteNoise para servir arquivos estáticos de forma eficiente (importante: deve ser a primeira app para runserver)
    'whitenoise.runserver_nostatic',
    
    # === NOVOS APPS CLOUDINARY ===
    'cloudinary',
    'cloudinary_storage',
    # ============================
    
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise deve vir logo abaixo do SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'davenport_downs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'davenport_downs.wsgi.application'


# ======================================================================
# DATABASE (AJUSTADO)
# ======================================================================
DATABASES = {
    'default': dj_database_url.config(
        # Render usa a variável de ambiente DATABASE_URL automaticamente.
        # Definimos um default seguro para o desenvolvimento local.
        default=config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3'),
        conn_max_age=600  # Adiciona conexão de pooling (opcional, mas recomendado)
    )
}
if not DEBUG and DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    # Este é um erro comum, se estiver em produção, o DB deve ser PostgreSQL ou similar,
    # não o db.sqlite3 local. Apenas um aviso de segurança.
    print("AVISO: Usando SQLite em produção. O Render PostgreSQL é recomendado.")


# Password validation
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
LANGUAGE_CODE = 'pt-br'

# >>> MUDANÇA CRÍTICA: FUSO HORÁRIO PARA ANGOLA (WAT) <<<
TIME_ZONE = 'Africa/Luanda'

USE_I18N = True

USE_TZ = True


# ======================================================================
# STATIC FILES (WHITENOISE)
# ======================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Pasta para onde os arquivos estáticos serão coletados em produção
STATICFILES_DIRS = [BASE_DIR / 'static'] # Pasta onde você armazena seus arquivos estáticos de desenvolvimento

# Configuração do WhiteNoise para servir arquivos estáticos otimizados (GZIP/Brotli e Manifest)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ======================================================================
# CONFIGURAÇÕES DE ARMAZENAMENTO DE ARQUIVOS (MEDIA FILES)
# ======================================================================

if not DEBUG:
    # ----------------------------------------------------------------------
    # 1. Configuração do Cloudinary (para Produção)
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': config('CLOUDINARY_API_KEY'),
        'API_SECRET': config('CLOUDINARY_API_SECRET'),
        # Opcional: Define um prefixo/pasta para os arquivos no Cloudinary
        'MEDIA_FOLDER': 'deposit_proofs',
    }
    
    # 2. Em Produção, use o Cloudinary como o método padrão para salvar arquivos
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    
    # Em produção, o Cloudinary gera a URL, mas mantemos o MEDIA_URL para consistência
    MEDIA_URL = '/media/'
    
else:
    # 3. Em Desenvolvimento (DEBUG=True), use o armazenamento local
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

    # Configurações para arquivos de mídia (ARMAZENAMENTO LOCAL)
    MEDIA_ROOT = BASE_DIR / 'media'
    MEDIA_URL = '/media/'

# ======================================================================
# FIM DA CONFIGURAÇÃO DE ARMAZENAMENTO
# ======================================================================


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# UKZ o modelo de usuário personalizado
AUTH_USER_MODEL = 'core.CustomUser'

LOGIN_URL = 'login'

# Configuração de segurança adicional para produção
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # HSTS (HTTP Strict Transport Security) - Importante!
    SECURE_HSTS_SECONDS = 31536000 # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Opcional, mas recomendado se você estiver usando um proxy/Load Balancer (como o Render)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    