"""
Integration tests for transaction views.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from inventory.models import Product, Category, StockTransaction
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
class TestTransactionCreateView:
    """Tests for TransactionCreateView"""
    
    def test_transaction_create_view_requires_login(self, client):
        """Test that transaction create view requires authentication"""
        url = reverse('transaction_create')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_transaction_create_view_displays_form(self, client, django_user_model):
        """Test that authenticated user can access transaction form"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        url = reverse('transaction_create')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'Record Transaction' in response.content.decode()
    
    def test_record_purchase_increases_quantity(self, client, django_user_model):
        """Test that recording a purchase increases product quantity"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Record purchase
        url = reverse('transaction_create')
        response = client.post(url, {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': 5
        })
        
        # Should redirect to transaction history
        assert response.status_code == 302
        assert response.url == reverse('transaction_history')
        
        # Check product quantity increased
        product.refresh_from_db()
        assert product.quantity == 15
        
        # Check transaction was logged
        assert StockTransaction.objects.filter(
            product=product,
            transaction_type='purchase',
            quantity_change=5
        ).exists()
    
    def test_record_sale_decreases_quantity(self, client, django_user_model):
        """Test that recording a sale decreases product quantity"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Record sale
        url = reverse('transaction_create')
        response = client.post(url, {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': 3
        })
        
        # Should redirect to transaction history
        assert response.status_code == 302
        
        # Check product quantity decreased
        product.refresh_from_db()
        assert product.quantity == 7
        
        # Check transaction was logged
        assert StockTransaction.objects.filter(
            product=product,
            transaction_type='sale',
            quantity_change=-3
        ).exists()
    
    def test_overselling_shows_error(self, client, django_user_model):
        """Test that attempting to oversell shows error message"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product with low stock
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=2,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Attempt to sell more than available
        url = reverse('transaction_create')
        response = client.post(url, {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': 5
        })
        
        # Should show form with error
        assert response.status_code == 200
        assert 'Insufficient inventory' in response.content.decode()
        
        # Check product quantity unchanged
        product.refresh_from_db()
        assert product.quantity == 2


@pytest.mark.django_db
class TestTransactionHistoryView:
    """Tests for TransactionHistoryView"""
    
    def test_transaction_history_requires_login(self, client):
        """Test that transaction history requires authentication"""
        url = reverse('transaction_history')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_transaction_history_displays_all_transactions(self, client, django_user_model):
        """Test that transaction history displays all transactions"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Create transactions
        StockTransaction.objects.create(
            product=product,
            user=user,
            transaction_type='purchase',
            quantity_change=5
        )
        StockTransaction.objects.create(
            product=product,
            user=user,
            transaction_type='sale',
            quantity_change=-3
        )
        
        # View transaction history
        url = reverse('transaction_history')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'transactions' in response.context
        assert len(response.context['transactions']) == 2
    
    def test_transaction_history_filtering_by_product(self, client, django_user_model):
        """Test filtering transactions by product"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and products
        category = Category.objects.create(name='Electronics')
        product1 = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        product2 = Product.objects.create(
            name='Mouse',
            quantity=50,
            price=Decimal('29.99'),
            category=category,
            alert_threshold=10
        )
        
        # Create transactions for both products
        StockTransaction.objects.create(
            product=product1,
            user=user,
            transaction_type='purchase',
            quantity_change=5
        )
        StockTransaction.objects.create(
            product=product2,
            user=user,
            transaction_type='purchase',
            quantity_change=10
        )
        
        # Filter by product1
        url = reverse('transaction_history')
        response = client.get(url, {'product': product1.id})
        
        assert response.status_code == 200
        transactions = response.context['transactions']
        assert len(transactions) == 1
        assert transactions[0].product == product1
    
    def test_transaction_history_filtering_by_type(self, client, django_user_model):
        """Test filtering transactions by type"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Create transactions of different types
        StockTransaction.objects.create(
            product=product,
            user=user,
            transaction_type='purchase',
            quantity_change=5
        )
        StockTransaction.objects.create(
            product=product,
            user=user,
            transaction_type='sale',
            quantity_change=-3
        )
        
        # Filter by purchase type
        url = reverse('transaction_history')
        response = client.get(url, {'transaction_type': 'purchase'})
        
        assert response.status_code == 200
        transactions = response.context['transactions']
        assert len(transactions) == 1
        assert transactions[0].transaction_type == 'purchase'


@pytest.mark.django_db
class TestValidateStock:
    """Tests for validate_stock HTMX endpoint"""
    
    def test_validate_stock_requires_login(self, client):
        """Test that validate_stock endpoint requires authentication"""
        url = reverse('validate_stock')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
    
    def test_validate_stock_for_sale_with_sufficient_inventory(self, client, django_user_model):
        """Test stock validation for sale with sufficient inventory"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Validate stock for sale
        url = reverse('validate_stock')
        response = client.get(url, {
            'product_id': product.id,
            'quantity': 5,
            'transaction_type': 'sale'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is True
        assert 'Current stock: 10' in data['message']
    
    def test_validate_stock_for_sale_with_insufficient_inventory(self, client, django_user_model):
        """Test stock validation for sale with insufficient inventory"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product with low stock
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=2,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Validate stock for sale exceeding available
        url = reverse('validate_stock')
        response = client.get(url, {
            'product_id': product.id,
            'quantity': 5,
            'transaction_type': 'sale'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is False
        assert 'Insufficient inventory' in data['message']
    
    def test_validate_stock_for_purchase(self, client, django_user_model):
        """Test stock validation for purchase (always valid)"""
        # Create user and login
        user = django_user_model.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Create category and product
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
        
        # Validate stock for purchase
        url = reverse('validate_stock')
        response = client.get(url, {
            'product_id': product.id,
            'quantity': 100,
            'transaction_type': 'purchase'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is True
