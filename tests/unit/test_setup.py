"""Test basic Django setup and configuration"""
import pytest
from django.conf import settings
from django.urls import reverse


@pytest.mark.unit
def test_django_settings_configured():
    """Verify Django settings are properly configured"""
    assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
    assert 'inventory' in settings.INSTALLED_APPS
    assert 'accounts' in settings.INSTALLED_APPS
    assert 'rest_framework' in settings.INSTALLED_APPS


@pytest.mark.unit
def test_static_files_configured():
    """Verify static files configuration"""
    assert settings.STATIC_URL is not None
    assert settings.STATICFILES_DIRS is not None


@pytest.mark.unit
def test_templates_configured():
    """Verify templates configuration"""
    templates = settings.TEMPLATES[0]
    assert templates['BACKEND'] == 'django.template.backends.django.DjangoTemplates'
    assert str(settings.BASE_DIR / 'templates') in [str(d) for d in templates['DIRS']]


@pytest.mark.unit
def test_authentication_configured():
    """Verify authentication settings"""
    assert settings.LOGIN_URL == 'login'
    assert settings.LOGIN_REDIRECT_URL == 'dashboard'
    assert settings.LOGOUT_REDIRECT_URL == 'login'


@pytest.mark.unit
def test_rest_framework_configured():
    """Verify REST framework configuration"""
    assert 'DEFAULT_AUTHENTICATION_CLASSES' in settings.REST_FRAMEWORK
    assert 'DEFAULT_PERMISSION_CLASSES' in settings.REST_FRAMEWORK
