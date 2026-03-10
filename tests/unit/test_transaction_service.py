"""
Unit tests for TransactionService.

Tests the business logic for transaction processing including
purchases, sales, overselling prevention, and transaction history.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from inventory.models import Product, Category, StockTransaction
from inventory.services import TransactionService, InsufficientInventoryError
from accounts.models import CustomUser


@pytest.fixture
def user(db):
    """Create a test user."""
    return CustomUser.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(
        name='Electronics',
        description='Electronic products'
    )


@pytest.fixture
def product(db, category):
    """Create a test product with initial quantity."""
    return Product.objects.create(
        name='Test Product',
        quantity=100,
        price=Decimal('19.99'),
        category=category,
        alert_threshold=10
    )


@pytest.fixture
def transaction_service():
    """Create TransactionService instance."""
    return TransactionService()


@pytest.mark.django_db
class TestRecordPurchase:
    """Tests for record_purchase method."""
    
    def test_record_purchase_increases_quantity(
        self, transaction_service, product, user
    ):
        """Test that recording a purchase increases product quantity."""
        initial_quantity = product.quantity
        purchase_quantity = 50
        
        transaction = transaction_service.record_purchase(
            product_id=product.id,
            quantity=purchase_quantity,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        
        assert product.quantity == initial_quantity + purchase_quantity
        assert transaction.transaction_type == 'purchase'
        assert transaction.quantity_change == purchase_quantity
        assert transaction.product == product
        assert transaction.user == user
    
    def test_record_purchase_creates_transaction_log(
        self, transaction_service, product, user
    ):
        """Test that purchase creates a transaction record."""
        transaction = transaction_service.record_purchase(
            product_id=product.id,
            quantity=25,
            user_id=user.id
        )
        
        assert StockTransaction.objects.filter(id=transaction.id).exists()
        assert transaction.timestamp is not None
    
    def test_record_purchase_rejects_zero_quantity(
        self, transaction_service, product, user
    ):
        """Test that zero quantity purchase is rejected."""
        with pytest.raises(ValidationError, match="must be positive"):
            transaction_service.record_purchase(
                product_id=product.id,
                quantity=0,
                user_id=user.id
            )
    
    def test_record_purchase_rejects_negative_quantity(
        self, transaction_service, product, user
    ):
        """Test that negative quantity purchase is rejected."""
        with pytest.raises(ValidationError, match="must be positive"):
            transaction_service.record_purchase(
                product_id=product.id,
                quantity=-10,
                user_id=user.id
            )
    
    def test_record_purchase_with_nonexistent_product(
        self, transaction_service, user
    ):
        """Test that purchase with invalid product ID raises error."""
        with pytest.raises(Product.DoesNotExist):
            transaction_service.record_purchase(
                product_id=99999,
                quantity=10,
                user_id=user.id
            )


@pytest.mark.django_db
class TestRecordSale:
    """Tests for record_sale method."""
    
    def test_record_sale_decreases_quantity(
        self, transaction_service, product, user
    ):
        """Test that recording a sale decreases product quantity."""
        initial_quantity = product.quantity
        sale_quantity = 30
        
        transaction = transaction_service.record_sale(
            product_id=product.id,
            quantity=sale_quantity,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        
        assert product.quantity == initial_quantity - sale_quantity
        assert transaction.transaction_type == 'sale'
        assert transaction.quantity_change == -sale_quantity
        assert transaction.product == product
        assert transaction.user == user
    
    def test_record_sale_creates_transaction_log(
        self, transaction_service, product, user
    ):
        """Test that sale creates a transaction record."""
        transaction = transaction_service.record_sale(
            product_id=product.id,
            quantity=15,
            user_id=user.id
        )
        
        assert StockTransaction.objects.filter(id=transaction.id).exists()
        assert transaction.timestamp is not None
    
    def test_record_sale_prevents_overselling(
        self, transaction_service, product, user
    ):
        """Test that overselling is prevented."""
        # Try to sell more than available
        with pytest.raises(InsufficientInventoryError, match="Only 100 available"):
            transaction_service.record_sale(
                product_id=product.id,
                quantity=150,
                user_id=user.id
            )
        
        # Verify quantity unchanged
        product.refresh_from_db()
        assert product.quantity == 100
    
    def test_record_sale_allows_exact_quantity(
        self, transaction_service, product, user
    ):
        """Test that selling exact available quantity works."""
        transaction = transaction_service.record_sale(
            product_id=product.id,
            quantity=100,
            user_id=user.id
        )
        
        product.refresh_from_db()
        assert product.quantity == 0
        assert transaction.quantity_change == -100
    
    def test_record_sale_rejects_zero_quantity(
        self, transaction_service, product, user
    ):
        """Test that zero quantity sale is rejected."""
        with pytest.raises(ValidationError, match="must be positive"):
            transaction_service.record_sale(
                product_id=product.id,
                quantity=0,
                user_id=user.id
            )
    
    def test_record_sale_rejects_negative_quantity(
        self, transaction_service, product, user
    ):
        """Test that negative quantity sale is rejected."""
        with pytest.raises(ValidationError, match="must be positive"):
            transaction_service.record_sale(
                product_id=product.id,
                quantity=-5,
                user_id=user.id
            )
    
    def test_record_sale_with_zero_stock(
        self, transaction_service, product, user
    ):
        """Test that sale fails when product has zero stock."""
        product.quantity = 0
        product.save()
        
        with pytest.raises(InsufficientInventoryError, match="Only 0 available"):
            transaction_service.record_sale(
                product_id=product.id,
                quantity=1,
                user_id=user.id
            )


@pytest.mark.django_db
class TestGetTransactionHistory:
    """Tests for get_transaction_history method."""
    
    def test_get_all_transactions(
        self, transaction_service, product, user
    ):
        """Test retrieving all transactions."""
        # Create multiple transactions
        transaction_service.record_purchase(product.id, 50, user.id)
        transaction_service.record_sale(product.id, 20, user.id)
        transaction_service.record_purchase(product.id, 30, user.id)
        
        transactions = transaction_service.get_transaction_history()
        
        assert transactions.count() == 3
    
    def test_get_transactions_ordered_by_timestamp_desc(
        self, transaction_service, product, user
    ):
        """Test that transactions are ordered by timestamp descending."""
        t1 = transaction_service.record_purchase(product.id, 10, user.id)
        t2 = transaction_service.record_sale(product.id, 5, user.id)
        t3 = transaction_service.record_purchase(product.id, 15, user.id)
        
        transactions = list(transaction_service.get_transaction_history())
        
        # Most recent first - verify ordering by checking timestamps
        assert transactions[0].timestamp >= transactions[1].timestamp
        assert transactions[1].timestamp >= transactions[2].timestamp
        
        # Verify all three transactions are present
        transaction_ids = {t.id for t in transactions}
        assert {t1.id, t2.id, t3.id} == transaction_ids
    
    def test_filter_by_product(
        self, transaction_service, product, category, user
    ):
        """Test filtering transactions by product."""
        # Create another product
        product2 = Product.objects.create(
            name='Product 2',
            quantity=50,
            price=Decimal('29.99'),
            category=category,
            alert_threshold=5
        )
        
        # Create transactions for both products
        transaction_service.record_purchase(product.id, 10, user.id)
        transaction_service.record_purchase(product2.id, 20, user.id)
        transaction_service.record_sale(product.id, 5, user.id)
        
        # Filter by first product
        transactions = transaction_service.get_transaction_history(
            product_id=product.id
        )
        
        assert transactions.count() == 2
        for t in transactions:
            assert t.product == product
    
    def test_filter_by_transaction_type(
        self, transaction_service, product, user
    ):
        """Test filtering transactions by type."""
        transaction_service.record_purchase(product.id, 10, user.id)
        transaction_service.record_sale(product.id, 5, user.id)
        transaction_service.record_purchase(product.id, 15, user.id)
        
        # Filter purchases
        purchases = transaction_service.get_transaction_history(
            transaction_type='purchase'
        )
        assert purchases.count() == 2
        for t in purchases:
            assert t.transaction_type == 'purchase'
        
        # Filter sales
        sales = transaction_service.get_transaction_history(
            transaction_type='sale'
        )
        assert sales.count() == 1
        assert sales[0].transaction_type == 'sale'
    
    def test_filter_by_date_range(
        self, transaction_service, product, user
    ):
        """Test filtering transactions by date range."""
        # Create transactions
        t1 = transaction_service.record_purchase(product.id, 10, user.id)
        t2 = transaction_service.record_sale(product.id, 5, user.id)
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Filter by today
        transactions = transaction_service.get_transaction_history(
            start_date=today,
            end_date=today
        )
        assert transactions.count() == 2
        
        # Filter by yesterday (should be empty)
        transactions = transaction_service.get_transaction_history(
            start_date=yesterday,
            end_date=yesterday
        )
        assert transactions.count() == 0
        
        # Filter from yesterday to tomorrow (should include all)
        transactions = transaction_service.get_transaction_history(
            start_date=yesterday,
            end_date=tomorrow
        )
        assert transactions.count() == 2
    
    def test_filter_by_start_date_only(
        self, transaction_service, product, user
    ):
        """Test filtering with only start date."""
        transaction_service.record_purchase(product.id, 10, user.id)
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        transactions = transaction_service.get_transaction_history(
            start_date=yesterday
        )
        assert transactions.count() == 1
    
    def test_filter_by_end_date_only(
        self, transaction_service, product, user
    ):
        """Test filtering with only end date."""
        transaction_service.record_purchase(product.id, 10, user.id)
        
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        transactions = transaction_service.get_transaction_history(
            end_date=tomorrow
        )
        assert transactions.count() == 1
    
    def test_combined_filters(
        self, transaction_service, product, category, user
    ):
        """Test combining multiple filters."""
        # Create another product
        product2 = Product.objects.create(
            name='Product 2',
            quantity=50,
            price=Decimal('29.99'),
            category=category,
            alert_threshold=5
        )
        
        # Create various transactions
        transaction_service.record_purchase(product.id, 10, user.id)
        transaction_service.record_sale(product.id, 5, user.id)
        transaction_service.record_purchase(product2.id, 20, user.id)
        
        today = timezone.now().date()
        
        # Filter: product1, purchases only, today
        transactions = transaction_service.get_transaction_history(
            product_id=product.id,
            transaction_type='purchase',
            start_date=today,
            end_date=today
        )
        
        assert transactions.count() == 1
        assert transactions[0].product == product
        assert transactions[0].transaction_type == 'purchase'
    
    def test_invalid_transaction_type(
        self, transaction_service
    ):
        """Test that invalid transaction type raises error."""
        with pytest.raises(ValidationError, match="must be 'purchase' or 'sale'"):
            transaction_service.get_transaction_history(
                transaction_type='invalid'
            )
