from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailAuthenticationBackend(ModelBackend):
    """Authenticate using email instead of username"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with email and password.
        
        Args:
            request: The HTTP request object
            username: Email address (named 'username' for compatibility with Django's auth system)
            password: User's password
            **kwargs: Additional keyword arguments
        
        Returns:
            User object if authentication succeeds, None otherwise
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
