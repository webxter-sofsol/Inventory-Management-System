"""
Unit tests for ProductService.

Tests CRUD operations and bulk update functionality.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from inventory.models import Product, Category
from inventory.services import ProductService


@pytest.fixture
def category(db):
    """Create a test category."""
    return Category.objects.create(name="Electronics", description="Electronic items")


@pytest.fixture
def product_service():
    """Create ProductService instance."""
    return ProductService()


@pytest.mark.django_db
class TestProductServiceCreate:
    """Tests for create_product method."""
    
    def test_create_product_with_valid_data(self, product_service, category):
        """Should create product with valid data."""
        product = product_service.create_product(
            name="Laptop",
            quantity=10,
            price=Decimal("999.99"),
            category=category,
            alert_threshold=5
        )
        
        assert product.id is not None
        assert product.name == "Laptop"
        assert product.quantity == 10
        assert product.price == Decimal("999.99")
        assert product.category == category
        assert product.alert_threshold == 5
    
    def test_create_product_with_negative_quantity_raises_error(self, product_service, category):
        """Should reject negative quantity."""
        with pytest.raises(ValidationError, match="Quantity cannot be negative"):
            product_service.create_product(
                name="Laptop",
                quantity=-5,
                price=Decimal("999.99"),
                category=category,
                alert_threshold=5
            )
    
    def test_create_product_with_zero_price_raises_error(self, product_service, category):
        """Should reject zero price."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            product_service.create_product(
                name="Laptop",
                quantity=10,
                price=Decimal("0"),
                category=category,
                alert_threshold=5
            )
    
    def test_create_product_with_negative_price_raises_error(self, product_service, category):
        """Should reject negative price."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            product_service.create_product(
                name="Laptop",
                quantity=10,
                price=Decimal("-10.00"),
                category=category,
                alert_threshold=5
            )
    
    def test_create_product_with_negative_threshold_raises_error(self, product_service, category):
        """Should reject negative alert threshold."""
        with pytest.raises(ValidationError, match="Alert threshold cannot be negative"):
            product_service.create_product(
                name="Laptop",
                quantity=10,
                price=Decimal("999.99"),
                category=category,
                alert_threshold=-1
            )


@pytest.mark.django_db
class TestProductServiceUpdate:
    """Tests for update_product method."""
    
    def test_update_product_name(self, product_service, category):
        """Should update product name."""
        product = Product.objects.create(
            name="Old Name",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updated = product_service.update_product(product.id, name="New Name")
        
        assert updated.name == "New Name"
        assert updated.quantity == 10  # Unchanged
    
    def test_update_product_quantity(self, product_service, category):
        """Should update product quantity."""
        product = Product.objects.create(
            name="Product",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updated = product_service.update_product(product.id, quantity=20)
        
        assert updated.quantity == 20
    
    def test_update_product_with_negative_quantity_raises_error(self, product_service, category):
        """Should reject negative quantity update."""
        product = Product.objects.create(
            name="Product",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        with pytest.raises(ValidationError, match="Quantity cannot be negative"):
            product_service.update_product(product.id, quantity=-5)
    
    def test_update_product_with_invalid_price_raises_error(self, product_service, category):
        """Should reject non-positive price update."""
        product = Product.objects.create(
            name="Product",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        with pytest.raises(ValidationError, match="Price must be positive"):
            product_service.update_product(product.id, price=Decimal("0"))
    
    def test_update_nonexistent_product_raises_error(self, product_service):
        """Should raise error for nonexistent product."""
        with pytest.raises(Product.DoesNotExist):
            product_service.update_product(99999, name="Test")


@pytest.mark.django_db
class TestProductServiceDelete:
    """Tests for delete_product method."""
    
    def test_delete_product(self, product_service, category):
        """Should delete product."""
        product = Product.objects.create(
            name="Product",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        product_service.delete_product(product.id)
        
        assert not Product.objects.filter(id=product.id).exists()
    
    def test_delete_nonexistent_product_raises_error(self, product_service):
        """Should raise error for nonexistent product."""
        with pytest.raises(Product.DoesNotExist):
            product_service.delete_product(99999)


@pytest.mark.django_db
class TestProductServiceSearch:
    """Tests for search_products method."""
    
    def test_search_by_name(self, product_service, category):
        """Should filter products by name."""
        Product.objects.create(
            name="Laptop Computer",
            quantity=10,
            price=Decimal("999.99"),
            category=category,
            alert_threshold=5
        )
        Product.objects.create(
            name="Desktop Computer",
            quantity=5,
            price=Decimal("799.99"),
            category=category,
            alert_threshold=3
        )
        Product.objects.create(
            name="Mouse",
            quantity=50,
            price=Decimal("19.99"),
            category=category,
            alert_threshold=10
        )
        
        results = product_service.search_products(query="Computer")
        
        assert results.count() == 2
        assert all("Computer" in p.name for p in results)
    
    def test_search_by_category(self, product_service):
        """Should filter products by category."""
        electronics = Category.objects.create(name="Electronics")
        furniture = Category.objects.create(name="Furniture")
        
        Product.objects.create(
            name="Laptop",
            quantity=10,
            price=Decimal("999.99"),
            category=electronics,
            alert_threshold=5
        )
        Product.objects.create(
            name="Chair",
            quantity=20,
            price=Decimal("199.99"),
            category=furniture,
            alert_threshold=5
        )
        
        results = product_service.search_products(category="Electronics")
        
        assert results.count() == 1
        assert results.first().name == "Laptop"
    
    def test_search_by_stock_status_out_of_stock(self, product_service, category):
        """Should filter out-of-stock products."""
        Product.objects.create(
            name="Product A",
            quantity=0,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        Product.objects.create(
            name="Product B",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        results = product_service.search_products(stock_status="out-of-stock")
        
        assert results.count() == 1
        assert results.first().name == "Product A"
    
    def test_search_by_stock_status_low_stock(self, product_service, category):
        """Should filter low-stock products."""
        Product.objects.create(
            name="Low Stock",
            quantity=3,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        Product.objects.create(
            name="In Stock",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        Product.objects.create(
            name="Out of Stock",
            quantity=0,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        results = product_service.search_products(stock_status="low-stock")
        
        assert results.count() == 1
        assert results.first().name == "Low Stock"
    
    def test_search_by_stock_status_in_stock(self, product_service, category):
        """Should filter in-stock products."""
        Product.objects.create(
            name="Low Stock",
            quantity=3,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        Product.objects.create(
            name="In Stock",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        results = product_service.search_products(stock_status="in-stock")
        
        assert results.count() == 1
        assert results.first().name == "In Stock"
    
    def test_search_with_multiple_filters(self, product_service):
        """Should apply multiple filters together."""
        electronics = Category.objects.create(name="Electronics")
        
        Product.objects.create(
            name="Laptop Computer",
            quantity=3,
            price=Decimal("999.99"),
            category=electronics,
            alert_threshold=5
        )
        Product.objects.create(
            name="Desktop Computer",
            quantity=10,
            price=Decimal("799.99"),
            category=electronics,
            alert_threshold=5
        )
        
        results = product_service.search_products(
            query="Computer",
            category="Electronics",
            stock_status="low-stock"
        )
        
        assert results.count() == 1
        assert results.first().name == "Laptop Computer"


@pytest.mark.django_db
class TestProductServiceBulkUpdateQuantities:
    """Tests for bulk_update_quantities method."""
    
    def test_bulk_update_quantities_success(self, product_service, category):
        """Should update multiple product quantities."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        p2 = Product.objects.create(
            name="Product 2",
            quantity=20,
            price=Decimal("60.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'quantity': 100},
            {'id': p2.id, 'quantity': 200}
        ]
        
        result = product_service.bulk_update_quantities(updates)
        
        assert len(result) == 2
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.quantity == 100
        assert p2.quantity == 200
    
    def test_bulk_update_quantities_with_invalid_data_rolls_back(self, product_service, category):
        """Should rollback all changes if any validation fails."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        p2 = Product.objects.create(
            name="Product 2",
            quantity=20,
            price=Decimal("60.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'quantity': 100},
            {'id': p2.id, 'quantity': -50}  # Invalid
        ]
        
        with pytest.raises(ValidationError, match="Quantity cannot be negative"):
            product_service.bulk_update_quantities(updates)
        
        # Verify no changes were made
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.quantity == 10  # Unchanged
        assert p2.quantity == 20  # Unchanged
    
    def test_bulk_update_quantities_missing_id_raises_error(self, product_service):
        """Should raise error if product ID is missing."""
        updates = [
            {'quantity': 100}  # Missing 'id'
        ]
        
        with pytest.raises(ValidationError, match="Product ID is required"):
            product_service.bulk_update_quantities(updates)
    
    def test_bulk_update_quantities_missing_quantity_raises_error(self, product_service, category):
        """Should raise error if quantity is missing."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id}  # Missing 'quantity'
        ]
        
        with pytest.raises(ValidationError, match="Quantity is required"):
            product_service.bulk_update_quantities(updates)
    
    def test_bulk_update_quantities_nonexistent_product_raises_error(self, product_service):
        """Should raise error if product doesn't exist."""
        updates = [
            {'id': 99999, 'quantity': 100}
        ]
        
        with pytest.raises(Product.DoesNotExist):
            product_service.bulk_update_quantities(updates)


@pytest.mark.django_db
class TestProductServiceBulkUpdatePrices:
    """Tests for bulk_update_prices method."""
    
    def test_bulk_update_prices_success(self, product_service, category):
        """Should update multiple product prices."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        p2 = Product.objects.create(
            name="Product 2",
            quantity=20,
            price=Decimal("60.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'price': Decimal("99.99")},
            {'id': p2.id, 'price': Decimal("149.99")}
        ]
        
        result = product_service.bulk_update_prices(updates)
        
        assert len(result) == 2
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.price == Decimal("99.99")
        assert p2.price == Decimal("149.99")
    
    def test_bulk_update_prices_with_string_conversion(self, product_service, category):
        """Should convert string prices to Decimal."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'price': "99.99"}  # String instead of Decimal
        ]
        
        result = product_service.bulk_update_prices(updates)
        
        p1.refresh_from_db()
        assert p1.price == Decimal("99.99")
    
    def test_bulk_update_prices_with_invalid_data_rolls_back(self, product_service, category):
        """Should rollback all changes if any validation fails."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        p2 = Product.objects.create(
            name="Product 2",
            quantity=20,
            price=Decimal("60.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'price': Decimal("99.99")},
            {'id': p2.id, 'price': Decimal("-10.00")}  # Invalid
        ]
        
        with pytest.raises(ValidationError, match="Price must be positive"):
            product_service.bulk_update_prices(updates)
        
        # Verify no changes were made
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p1.price == Decimal("50.00")  # Unchanged
        assert p2.price == Decimal("60.00")  # Unchanged
    
    def test_bulk_update_prices_with_zero_price_raises_error(self, product_service, category):
        """Should reject zero price."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'price': Decimal("0")}
        ]
        
        with pytest.raises(ValidationError, match="Price must be positive"):
            product_service.bulk_update_prices(updates)
    
    def test_bulk_update_prices_missing_id_raises_error(self, product_service):
        """Should raise error if product ID is missing."""
        updates = [
            {'price': Decimal("99.99")}  # Missing 'id'
        ]
        
        with pytest.raises(ValidationError, match="Product ID is required"):
            product_service.bulk_update_prices(updates)
    
    def test_bulk_update_prices_missing_price_raises_error(self, product_service, category):
        """Should raise error if price is missing."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id}  # Missing 'price'
        ]
        
        with pytest.raises(ValidationError, match="Price is required"):
            product_service.bulk_update_prices(updates)
    
    def test_bulk_update_prices_invalid_format_raises_error(self, product_service, category):
        """Should raise error for invalid price format."""
        p1 = Product.objects.create(
            name="Product 1",
            quantity=10,
            price=Decimal("50.00"),
            category=category,
            alert_threshold=5
        )
        
        updates = [
            {'id': p1.id, 'price': "invalid"}
        ]
        
        with pytest.raises(ValidationError, match="Invalid price format"):
            product_service.bulk_update_prices(updates)
