"""Unit tests for authentication views

Tests cover:
- Valid login redirects to dashboard
- Invalid credentials show error message
- Session expiration redirects to login
- Duplicate email registration fails
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from accounts.views import login_view

User = get_user_model()


@pytest.mark.unit
class TestLoginView:
    """Test cases for login view functionality"""
    
    def test_valid_login_redirects_to_dashboard(self, client, user):
        """Test that valid login credentials redirect to dashboard
        
        Validates: Requirements 1.1
        """
        url = reverse('login')
        response = client.post(url, {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.url == reverse('dashboard')
        
        # User should be authenticated
        response = client.get(reverse('dashboard'))
        assert response.wsgi_request.user.is_authenticated
        assert response.wsgi_request.user.email == 'test@example.com'
    
    def test_valid_login_with_next_parameter(self, client, user):
        """Test that valid login redirects to 'next' URL if provided
        
        Validates: Requirements 1.1
        """
        url = reverse('login') + '?next=/inventory/products/'
        response = client.post(url, {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should redirect to the 'next' URL
        assert response.status_code == 302
        assert '/inventory/products/' in response.url
    
    def test_invalid_email_shows_error_message(self, client, user):
        """Test that invalid email shows error message
        
        Validates: Requirements 1.2
        """
        url = reverse('login')
        response = client.post(url, {
            'username': 'wrong@example.com',
            'password': 'testpass123'
        })
        
        # Should not redirect (stays on login page)
        assert response.status_code == 200
        
        # Should display error message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert 'Invalid email or password' in str(messages[0])
        
        # User should not be authenticated
        assert not response.wsgi_request.user.is_authenticated
    
    def test_invalid_password_shows_error_message(self, client, user):
        """Test that invalid password shows error message
        
        Validates: Requirements 1.2
        """
        url = reverse('login')
        response = client.post(url, {
            'username': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        # Should not redirect (stays on login page)
        assert response.status_code == 200
        
        # Should display error message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert 'Invalid email or password' in str(messages[0])
        
        # User should not be authenticated
        assert not response.wsgi_request.user.is_authenticated
    
    def test_empty_credentials_shows_error(self, client):
        """Test that empty credentials show error message
        
        Validates: Requirements 1.2
        """
        url = reverse('login')
        response = client.post(url, {
            'username': '',
            'password': ''
        })
        
        # Should not redirect (stays on login page)
        assert response.status_code == 200
        
        # Should display error message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert 'Invalid email or password' in str(messages[0])
    
    def test_login_page_renders_correctly(self, client):
        """Test that login page renders with form
        
        Validates: Requirements 1.1
        """
        url = reverse('login')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert b'Email' in response.content or b'email' in response.content
        assert b'Password' in response.content or b'password' in response.content
    
    def test_authenticated_user_redirects_from_login(self, authenticated_client):
        """Test that already authenticated users are redirected from login page
        
        Validates: Requirements 1.1
        """
        url = reverse('login')
        response = authenticated_client.get(url)
        
        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.url == reverse('dashboard')


@pytest.mark.unit
class TestSessionExpiration:
    """Test cases for session expiration and authentication requirements"""
    
    def test_session_expiration_redirects_to_login(self, client, user):
        """Test that expired session redirects to login page
        
        Validates: Requirements 1.4
        """
        # First, login the user
        client.login(username=user.email, password='testpass123')
        
        # Verify user is authenticated
        response = client.get(reverse('dashboard'))
        assert response.wsgi_request.user.is_authenticated
        
        # Simulate session expiration by logging out
        client.logout()
        
        # Try to access protected page
        response = client.get(reverse('dashboard'))
        
        # Should redirect to login page
        assert response.status_code == 302
        assert reverse('login') in response.url
    
    def test_unauthenticated_access_redirects_to_login(self, client):
        """Test that unauthenticated users are redirected to login
        
        Validates: Requirements 1.4
        """
        # Try to access protected dashboard without authentication
        response = client.get(reverse('dashboard'))
        
        # Should redirect to login page
        assert response.status_code == 302
        assert reverse('login') in response.url
    
    def test_login_preserves_next_parameter_after_session_expiration(self, client):
        """Test that 'next' parameter is preserved when redirecting to login
        
        Validates: Requirements 1.4
        """
        # Try to access protected page without authentication
        protected_url = reverse('dashboard')
        response = client.get(protected_url)
        
        # Should redirect to login with 'next' parameter
        assert response.status_code == 302
        assert reverse('login') in response.url
        assert 'next=' in response.url


@pytest.mark.unit
class TestRegistrationView:
    """Test cases for user registration functionality"""
    
    def test_duplicate_email_registration_fails(self, client, user):
        """Test that registering with duplicate email fails
        
        Validates: Requirements 1.3
        """
        url = reverse('register')
        response = client.post(url, {
            'email': 'test@example.com',  # This email already exists
            'password1': 'newpass123',
            'password2': 'newpass123'
        })
        
        # Should not redirect (stays on registration page)
        assert response.status_code == 200
        
        # Should display error message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        error_text = ' '.join([str(m) for m in messages])
        assert 'already exists' in error_text.lower() or 'duplicate' in error_text.lower()
        
        # Should not create a new user
        assert User.objects.filter(email='test@example.com').count() == 1
    
    def test_successful_registration_redirects_to_login(self, client, db):
        """Test that successful registration redirects to login page
        
        Validates: Requirements 1.1, 1.3
        """
        url = reverse('register')
        response = client.post(url, {
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123'
        })
        
        # Should redirect to login page
        assert response.status_code == 302
        assert response.url == reverse('login')
        
        # User should be created
        assert User.objects.filter(email='newuser@example.com').exists()
        
        # Should display success message
        messages = list(response.wsgi_request._messages)
        assert len(messages) > 0
        assert 'success' in str(messages[0]).lower() or 'created' in str(messages[0]).lower()
    
    def test_password_mismatch_fails_registration(self, client, db):
        """Test that mismatched passwords fail registration
        
        Validates: Requirements 1.1
        """
        url = reverse('register')
        response = client.post(url, {
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'differentpass123'
        })
        
        # Should not redirect (stays on registration page)
        assert response.status_code == 200
        
        # User should not be created
        assert not User.objects.filter(email='newuser@example.com').exists()
    
    def test_invalid_email_format_fails_registration(self, client, db):
        """Test that invalid email format fails registration
        
        Validates: Requirements 1.3
        """
        url = reverse('register')
        response = client.post(url, {
            'email': 'not-an-email',
            'password1': 'securepass123',
            'password2': 'securepass123'
        })
        
        # Should not redirect (stays on registration page)
        assert response.status_code == 200
        
        # User should not be created
        assert not User.objects.filter(email='not-an-email').exists()
    
    def test_registration_page_renders_correctly(self, client):
        """Test that registration page renders with form
        
        Validates: Requirements 1.1
        """
        url = reverse('register')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert b'Email' in response.content or b'email' in response.content
        assert b'Password' in response.content or b'password' in response.content
    
    def test_authenticated_user_redirects_from_register(self, authenticated_client):
        """Test that already authenticated users are redirected from registration page
        
        Validates: Requirements 1.1
        """
        url = reverse('register')
        response = authenticated_client.get(url)
        
        # Should redirect to dashboard
        assert response.status_code == 302
        assert response.url == reverse('dashboard')


@pytest.mark.unit
class TestLogoutView:
    """Test cases for logout functionality"""
    
    def test_logout_clears_session(self, authenticated_client):
        """Test that logout clears user session
        
        Validates: Requirements 1.1
        """
        # Verify user is authenticated
        response = authenticated_client.get(reverse('dashboard'))
        assert response.wsgi_request.user.is_authenticated
        
        # Logout
        url = reverse('logout')
        response = authenticated_client.post(url)
        
        # Should redirect to login page
        assert response.status_code == 302
        assert response.url == reverse('login')
        
        # User should no longer be authenticated
        response = authenticated_client.get(reverse('dashboard'))
        assert response.status_code == 302  # Redirected to login
    
    def test_logout_requires_post_method(self, authenticated_client):
        """Test that logout requires POST method for security
        
        Validates: Requirements 1.1
        """
        url = reverse('logout')
        response = authenticated_client.get(url)
        
        # GET request should render confirmation page, not logout
        assert response.status_code == 200
        
        # User should still be authenticated after GET
        response = authenticated_client.get(reverse('dashboard'))
        assert response.wsgi_request.user.is_authenticated
