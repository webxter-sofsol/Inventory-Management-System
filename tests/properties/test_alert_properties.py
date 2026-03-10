"""
Property-based tests for Alert Management

Feature: inventory-management-system

These tests validate universal correctness properties for the alert system
using Hypothesis. Each property should hold true for all valid inputs.
"""
import pytest
from decimal import Decimal
from hypothesis import given, strategies as st, assume
from django.core.exceptions import ValidationError

from inventory.models import Product, Category, LowStockAlert
from inventory.services import AlertService


# Hypothesis strategies for generating test data
@st.composite
def product_with_threshold(draw, below_threshold=True):
    """
    Generate a product with quantity relative to alert threshold.
    
    Args:
        below_threshold: If True, quantity < threshold (low stock)
                        If False, quantity >= threshold (sufficient stock)
    """
    threshold = draw(st.integers(min_value=1, max_value=100))
    
    if below_threshold:
        # Generate quantity below threshold (0 to threshold-1)
        quantity = draw(st.integers(min_value=0, max_value=threshold - 1))
    else:
        # Generate quantity at or above threshold
        quantity = draw(st.integers(min_value=threshold, max_value=threshold + 1000))
    
    return {
        'quantity': quantity,
        'threshold': threshold,
    }


def get_or_create_test_category():
    """Get or create a test category for property tests"""
    category, _ = Category.objects.get_or_create(
        name="Test Category",
        defaults={'description': "Test Description"}
    )
    return category


@pytest.mark.django_db
@pytest.mark.property
class TestAlertProperties:
    """Property-based tests for Alert Management correctness"""
    
    @given(data=st.data())
    def test_property_13_alert_generation_on_low_stock(self, data):
        """
        Property 13: Alert Generation on Low Stock
        
        For any product, when its quantity falls below its alert threshold,
        an active low-stock alert should exist for that product.
        
        Validates: Requirements 4.1
        Feature: inventory-management-system, Property 13: Alert Generation on Low Stock
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Generate product data with quantity below threshold
        product_data = data.draw(product_with_threshold(below_threshold=True))
        
        # Create product with low stock
        product = Product.objects.create(
            name=f"LowStockProduct_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=product_data['quantity'],
            price=Decimal('10.00'),
            category=category,
            alert_threshold=product_data['threshold']
        )
        
        # Verify product is below threshold
        assert product.quantity < product.alert_threshold, \
            f"Product quantity {product.quantity} should be below threshold {product.alert_threshold}"
        
        # Check and create alert
        alert = AlertService.check_and_create_alert(product)
        
        # Alert should be created
        assert alert is not None, \
            f"Alert should be created for product with quantity {product.quantity} < threshold {product.alert_threshold}"
        
        # Alert should be active
        assert alert.is_active, "Alert should be active"
        
        # Alert should be associated with the product
        assert alert.product == product, "Alert should be associated with the correct product"
        
        # Verify alert exists in database
        db_alert = LowStockAlert.objects.get(product=product)
        assert db_alert.is_active, "Alert in database should be active"
        assert db_alert.product == product, "Alert in database should be associated with the correct product"
    
    @given(data=st.data())
    def test_property_14_alert_resolution_on_stock_increase(self, data):
        """
        Property 14: Alert Resolution on Stock Increase
        
        For any product with an active low-stock alert, when its quantity rises
        to or above its alert threshold, the alert should be removed or marked inactive.
        
        Validates: Requirements 4.4
        Feature: inventory-management-system, Property 14: Alert Resolution on Stock Increase
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Generate threshold
        threshold = data.draw(st.integers(min_value=10, max_value=100))
        
        # Create product with low stock (below threshold)
        low_quantity = data.draw(st.integers(min_value=0, max_value=threshold - 1))
        product = Product.objects.create(
            name=f"ResolvableProduct_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=low_quantity,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=threshold
        )
        
        # Create alert for low stock product
        alert = LowStockAlert.objects.create(
            product=product,
            is_active=True
        )
        
        # Verify alert exists and is active
        assert LowStockAlert.objects.filter(product=product, is_active=True).exists(), \
            "Alert should exist before resolution"
        
        # Increase product quantity to or above threshold
        new_quantity = data.draw(st.integers(min_value=threshold, max_value=threshold + 1000))
        product.quantity = new_quantity
        product.save()
        
        # Verify product is now at or above threshold
        assert product.quantity >= product.alert_threshold, \
            f"Product quantity {product.quantity} should be >= threshold {product.alert_threshold}"
        
        # Resolve alert
        AlertService.resolve_alert(product)
        
        # Alert should be removed (deleted from database)
        assert not LowStockAlert.objects.filter(product=product).exists(), \
            f"Alert should be removed when quantity {product.quantity} >= threshold {product.alert_threshold}"
    
    @given(data=st.data())
    def test_property_15_alert_threshold_configuration(self, data):
        """
        Property 15: Alert Threshold Configuration
        
        For any product and non-negative threshold value, setting the alert
        threshold should result in that threshold being stored and used for
        alert generation.
        
        Validates: Requirements 4.3
        Feature: inventory-management-system, Property 15: Alert Threshold Configuration
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Generate valid threshold (non-negative)
        threshold = data.draw(st.integers(min_value=0, max_value=10000))
        
        # Create product with the threshold
        product = Product.objects.create(
            name=f"ConfigurableProduct_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=data.draw(st.integers(min_value=0, max_value=1000)),
            price=Decimal('10.00'),
            category=category,
            alert_threshold=threshold
        )
        
        # Verify threshold is stored correctly
        assert product.alert_threshold == threshold, \
            f"Alert threshold should be {threshold} but got {product.alert_threshold}"
        
        # Retrieve product from database and verify persistence
        retrieved_product = Product.objects.get(id=product.id)
        assert retrieved_product.alert_threshold == threshold, \
            f"Persisted alert threshold should be {threshold} but got {retrieved_product.alert_threshold}"
        
        # Test threshold is used for alert generation
        # Case 1: Quantity below threshold should trigger alert
        if product.quantity < threshold:
            alert = AlertService.check_and_create_alert(product)
            assert alert is not None, \
                f"Alert should be created when quantity {product.quantity} < threshold {threshold}"
        
        # Case 2: Update threshold and verify it's used
        new_threshold = data.draw(st.integers(min_value=0, max_value=10000))
        product.alert_threshold = new_threshold
        product.save()
        
        # Verify new threshold is stored
        product.refresh_from_db()
        assert product.alert_threshold == new_threshold, \
            f"Updated alert threshold should be {new_threshold} but got {product.alert_threshold}"
        
        # Verify new threshold is used for alert logic
        if product.quantity < new_threshold:
            # Should create/maintain alert
            alert = AlertService.check_and_create_alert(product)
            assert alert is not None, \
                f"Alert should exist when quantity {product.quantity} < new threshold {new_threshold}"
        else:
            # Should not have alert (or should resolve it)
            AlertService.resolve_alert(product)
            assert not LowStockAlert.objects.filter(product=product).exists(), \
                f"Alert should not exist when quantity {product.quantity} >= new threshold {new_threshold}"
    
    @given(threshold=st.integers(max_value=-1))
    def test_property_16_alert_threshold_validation(self, threshold):
        """
        Property 16: Alert Threshold Validation
        
        For any negative threshold value, attempting to set it as an alert
        threshold should be rejected by validation.
        
        Validates: Requirements 4.5
        Feature: inventory-management-system, Property 16: Alert Threshold Validation
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Attempt to create product with negative alert threshold
        product = Product(
            name="InvalidThresholdProduct",
            quantity=10,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=threshold  # Negative value
        )
        
        # Validation should fail
        with pytest.raises(ValidationError):
            product.full_clean()
        
        # Also test updating existing product with negative threshold
        valid_product = Product.objects.create(
            name="ValidProduct",
            quantity=10,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=5
        )
        
        # Attempt to update with negative threshold
        valid_product.alert_threshold = threshold
        
        # Validation should fail
        with pytest.raises(ValidationError):
            valid_product.full_clean()
