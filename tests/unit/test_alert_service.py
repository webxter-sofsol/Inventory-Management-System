"""
Unit tests for AlertService.

Tests the alert management business logic including alert creation,
resolution, and retrieval.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from inventory.models import Product, Category, LowStockAlert
from inventory.services import AlertService


@pytest.mark.django_db
class TestAlertService:
    """Test suite for AlertService."""
    
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
            quantity=50,
            price=Decimal("10.00"),
            category=category,
            alert_threshold=20
        )
    
    def test_check_and_create_alert_when_below_threshold(self, product):
        """Test that alert is created when quantity falls below threshold."""
        # Set quantity below threshold
        product.quantity = 15
        product.save()
        
        # Check and create alert
        alert = AlertService.check_and_create_alert(product)
        
        # Verify alert was created
        assert alert is not None
        assert alert.product == product
        assert alert.is_active is True
        
        # Verify alert exists in database
        assert LowStockAlert.objects.filter(product=product).exists()
    
    def test_check_and_create_alert_when_above_threshold(self, product):
        """Test that no alert is created when quantity is above threshold."""
        # Quantity is already above threshold (50 >= 20)
        
        # Check and create alert
        alert = AlertService.check_and_create_alert(product)
        
        # Verify no alert was created
        assert alert is None
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_check_and_create_alert_reactivates_inactive_alert(self, product):
        """Test that inactive alert is reactivated when quantity falls below threshold."""
        # Create an inactive alert
        existing_alert = LowStockAlert.objects.create(
            product=product,
            is_active=False
        )
        
        # Set quantity below threshold
        product.quantity = 10
        product.save()
        
        # Check and create alert
        alert = AlertService.check_and_create_alert(product)
        
        # Verify alert was reactivated
        assert alert is not None
        assert alert.id == existing_alert.id
        assert alert.is_active is True
    
    def test_check_and_create_alert_does_not_duplicate(self, product):
        """Test that duplicate alerts are not created."""
        # Set quantity below threshold
        product.quantity = 10
        product.save()
        
        # Create alert first time
        alert1 = AlertService.check_and_create_alert(product)
        
        # Try to create alert again
        alert2 = AlertService.check_and_create_alert(product)
        
        # Verify same alert is returned
        assert alert1.id == alert2.id
        
        # Verify only one alert exists
        assert LowStockAlert.objects.filter(product=product).count() == 1
    
    def test_resolve_alert_removes_alert_when_above_threshold(self, product):
        """Test that alert is removed when quantity rises above threshold."""
        # Create an alert
        LowStockAlert.objects.create(product=product, is_active=True)
        
        # Set quantity above threshold
        product.quantity = 30
        product.save()
        
        # Resolve alert
        AlertService.resolve_alert(product)
        
        # Verify alert was deleted
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_resolve_alert_does_nothing_when_no_alert_exists(self, product):
        """Test that resolve_alert handles missing alerts gracefully."""
        # Set quantity above threshold
        product.quantity = 30
        product.save()
        
        # Resolve alert (no alert exists)
        AlertService.resolve_alert(product)
        
        # Should not raise any exception
        assert not LowStockAlert.objects.filter(product=product).exists()
    
    def test_resolve_alert_does_not_remove_when_below_threshold(self, product):
        """Test that alert is not removed when quantity is still below threshold."""
        # Create an alert
        alert = LowStockAlert.objects.create(product=product, is_active=True)
        
        # Set quantity below threshold
        product.quantity = 15
        product.save()
        
        # Try to resolve alert
        AlertService.resolve_alert(product)
        
        # Verify alert still exists (quantity still below threshold)
        assert LowStockAlert.objects.filter(product=product).exists()
    
    def test_get_active_alerts_returns_only_active(self, category):
        """Test that get_active_alerts returns only active alerts."""
        # Create products with alerts
        product1 = Product.objects.create(
            name="Product 1",
            quantity=5,
            price=Decimal("10.00"),
            category=category,
            alert_threshold=10
        )
        product2 = Product.objects.create(
            name="Product 2",
            quantity=3,
            price=Decimal("15.00"),
            category=category,
            alert_threshold=10
        )
        product3 = Product.objects.create(
            name="Product 3",
            quantity=8,
            price=Decimal("20.00"),
            category=category,
            alert_threshold=10
        )
        
        # Create alerts
        LowStockAlert.objects.create(product=product1, is_active=True)
        LowStockAlert.objects.create(product=product2, is_active=True)
        LowStockAlert.objects.create(product=product3, is_active=False)
        
        # Get active alerts
        active_alerts = AlertService.get_active_alerts()
        
        # Verify only active alerts are returned
        assert active_alerts.count() == 2
        assert product1 in [alert.product for alert in active_alerts]
        assert product2 in [alert.product for alert in active_alerts]
        assert product3 not in [alert.product for alert in active_alerts]
    
    def test_get_active_alerts_returns_empty_when_none_exist(self):
        """Test that get_active_alerts returns empty queryset when no alerts exist."""
        # Get active alerts
        active_alerts = AlertService.get_active_alerts()
        
        # Verify empty queryset
        assert active_alerts.count() == 0
