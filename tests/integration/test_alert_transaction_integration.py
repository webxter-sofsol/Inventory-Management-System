"""
Integration tests for alert and transaction interaction.

Tests that alerts are properly created and resolved when transactions
affect product quantities.
"""

import pytest
from decimal import Decimal
from inventory.models import Product, Category, LowStockAlert, StockTransaction
from inventory.services import TransactionService, AlertService
from accounts.models import CustomUser


@pytest.mark.django_db
class TestAlertTransactionIntegration:
    """Test suite for alert and transaction integration."""
    
    @pytest.fixture
    def user(self):
        """Create a test user."""
        return CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
    
    @pytest.fixture
    def category(self):
        """Create a test category."""
        return Category.objects.create(
            name="Test Category",
            description="Test category description"
        )
    
    @pytest.fixture
    def product(self, category):
        """Create a test product with alert threshold."""
        return Product.objects.create(
            name="Test Product",
            quantity=25,
            price=Decimal("10.00"),
            category=category,
            alert_threshold=20
        )
    
    def test_sale_creates_alert_when_quantity_falls_below_threshold(self, product, user):
        """Test that recording a sale creates an alert when quantity falls below threshold."""
        # Initial quantity: 25, threshold: 20
        # Sell 10 units -> quantity becomes 15 (below threshold)
        
        # Record sale
        transaction = TransactionService().record_sale(
            product_id=product.id,
            quantity=10,
            user_id=user.id
        )
        
        # Verify transaction was recorded
        assert transaction.transaction_type == 'sale'
        assert transaction.quantity_change == -10
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 15
        
        # Verify alert was created
        assert LowStockAlert.objects.filter(product=product, is_active=True).exists()
        alert = LowStockAlert.objects.get(product=product)
        assert alert.is_active is True
    
    def test_sale_does_not_create_alert_when_quantity_stays_above_threshold(self, product, user):
        """Test that recording a sale does not create an alert when quantity stays above threshold."""
        # Initial quantity: 25, threshold: 20
        # Sell 3 units -> quantity becomes 22 (still above threshold)
        
        # Record sale
        transaction = TransactionService().record_sale(
            product_id=product.id,
            quantity=3,
            user_id=user.id
        )
        
        # Verify transaction was recorded
        assert transaction.transaction_type == 'sale'
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 22
        
        # Verify no alert was created
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_purchase_resolves_alert_when_quantity_rises_above_threshold(self, product, user):
        """Test that recording a purchase resolves an alert when quantity rises above threshold."""
        # Set product below threshold and create alert
        product.quantity = 15
        product.save()
        alert = LowStockAlert.objects.create(product=product, is_active=True)
        
        # Record purchase to bring quantity above threshold
        # 15 + 10 = 25 (above threshold of 20)
        transaction = TransactionService().record_purchase(
            product_id=product.id,
            quantity=10,
            user_id=user.id
        )
        
        # Verify transaction was recorded
        assert transaction.transaction_type == 'purchase'
        assert transaction.quantity_change == 10
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 25
        
        # Verify alert was deleted
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_purchase_does_not_resolve_alert_when_quantity_stays_below_threshold(self, product, user):
        """Test that recording a purchase does not resolve alert when quantity stays below threshold."""
        # Set product below threshold and create alert
        product.quantity = 10
        product.save()
        alert = LowStockAlert.objects.create(product=product, is_active=True)
        
        # Record purchase but keep quantity below threshold
        # 10 + 5 = 15 (still below threshold of 20)
        transaction = TransactionService().record_purchase(
            product_id=product.id,
            quantity=5,
            user_id=user.id
        )
        
        # Verify transaction was recorded
        assert transaction.transaction_type == 'purchase'
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 15
        
        # Verify alert still exists
        assert LowStockAlert.objects.filter(product=product, is_active=True).exists()
    
    def test_multiple_sales_maintain_single_alert(self, product, user):
        """Test that multiple sales below threshold maintain a single alert."""
        # Initial quantity: 25, threshold: 20
        
        # First sale: 25 - 10 = 15 (creates alert)
        TransactionService().record_sale(
            product_id=product.id,
            quantity=10,
            user_id=user.id
        )
        
        # Verify alert was created
        assert LowStockAlert.objects.filter(product=product).count() == 1
        
        # Second sale: 15 - 5 = 10 (should not create duplicate alert)
        TransactionService().record_sale(
            product_id=product.id,
            quantity=5,
            user_id=user.id
        )
        
        # Verify still only one alert exists
        assert LowStockAlert.objects.filter(product=product).count() == 1
        
        # Verify product quantity
        product.refresh_from_db()
        assert product.quantity == 10
    
    def test_sale_to_zero_creates_alert(self, product, user):
        """Test that selling all stock creates an alert."""
        # Initial quantity: 25, threshold: 20
        # Sell all 25 units -> quantity becomes 0 (below threshold)
        
        # Record sale
        TransactionService().record_sale(
            product_id=product.id,
            quantity=25,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 0
        
        # Verify alert was created
        assert LowStockAlert.objects.filter(product=product, is_active=True).exists()
    
    def test_purchase_from_zero_resolves_alert_if_above_threshold(self, product, user):
        """Test that purchasing from zero stock resolves alert if quantity goes above threshold."""
        # Set product to zero and create alert
        product.quantity = 0
        product.save()
        alert = LowStockAlert.objects.create(product=product, is_active=True)
        
        # Purchase enough to go above threshold
        # 0 + 25 = 25 (above threshold of 20)
        TransactionService().record_purchase(
            product_id=product.id,
            quantity=25,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        assert product.quantity == 25
        
        # Verify alert was deleted
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_get_active_alerts_reflects_transaction_changes(self, category, user):
        """Test that get_active_alerts reflects changes from transactions."""
        # Create multiple products
        product1 = Product.objects.create(
            name="Product 1",
            quantity=30,
            price=Decimal("10.00"),
            category=category,
            alert_threshold=20
        )
        product2 = Product.objects.create(
            name="Product 2",
            quantity=30,
            price=Decimal("15.00"),
            category=category,
            alert_threshold=20
        )
        
        # Initially no alerts
        assert AlertService.get_active_alerts().count() == 0
        
        # Sell product1 below threshold
        TransactionService().record_sale(
            product_id=product1.id,
            quantity=15,
            user_id=user.id
        )
        
        # Should have 1 alert
        active_alerts = AlertService.get_active_alerts()
        assert active_alerts.count() == 1
        assert active_alerts.first().product == product1
        
        # Sell product2 below threshold
        TransactionService().record_sale(
            product_id=product2.id,
            quantity=20,
            user_id=user.id
        )
        
        # Should have 2 alerts
        active_alerts = AlertService.get_active_alerts()
        assert active_alerts.count() == 2
        
        # Purchase product1 above threshold
        TransactionService().record_purchase(
            product_id=product1.id,
            quantity=10,
            user_id=user.id
        )
        
        # Should have 1 alert (only product2)
        active_alerts = AlertService.get_active_alerts()
        assert active_alerts.count() == 1
        assert active_alerts.first().product == product2
