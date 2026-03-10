"""Pytest configuration and fixtures for inventory management system tests"""
import pytest
from django.contrib.auth import get_user_model
from hypothesis import settings, Verbosity

# Configure Hypothesis settings
settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=100)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile("dev")

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user"""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def authenticated_client(client, user):
    """Create an authenticated client"""
    client.login(username=user.email, password="testpass123")
    return client
