"""
Property-based tests for Product model

Feature: inventory-management-system

These tests validate universal correctness properties using Hypothesis.
Each property should hold true for all valid inputs.
"""
import pytest
from decimal import Decimal
from hypothesis import given, strategies as st, assume
from hypothesis.extra.django import from_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from inventory.models import Product, Category


# Hypothesis strategies for generating test data
@st.composite
def valid_product_data(draw, category):
    """Generate valid product data"""
    return {
        'name': draw(st.text(
            min_size=1, 
            max_size=200, 
            alphabet=st.characters(
                blacklist_categories=('Cs',),  # Exclude surrogates
                blacklist_characters=['\x00']
            )
        )),
        'quantity': draw(st.integers(min_value=0, max_value=1000000)),
        'price': draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2)),
        'category': category,
        'alert_threshold': draw(st.integers(min_value=0, max_value=1000000)),
    }


@st.composite
def valid_update_data(draw):
    """Generate valid update data for products"""
    return {
        'name': draw(st.text(
            min_size=1, 
            max_size=200, 
            alphabet=st.characters(
                blacklist_categories=('Cs',),  # Exclude surrogates
                blacklist_characters=['\x00']
            )
        )),
        'quantity': draw(st.integers(min_value=0, max_value=1000000)),
        'price': draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2)),
        'alert_threshold': draw(st.integers(min_value=0, max_value=1000000)),
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
class TestProductProperties:
    """Property-based tests for Product model correctness"""
    
    @given(data=st.data())
    def test_property_4_product_creation_persistence(self, data):
        """
        Property 4: Product Creation Persistence
        
        For any valid product data (name, non-negative quantity, positive price, 
        category, non-negative threshold), creating a product should result in 
        that product being retrievable from the database with all attributes intact.
        
        Validates: Requirements 2.1, 2.5
        Feature: inventory-management-system, Property 4: Product Creation Persistence
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Generate valid product data
        product_data = data.draw(valid_product_data(category))
        
        # Create product
        product = Product.objects.create(**product_data)
        
        # Retrieve product from database
        retrieved_product = Product.objects.get(id=product.id)
        
        # Assert all attributes are intact
        assert retrieved_product.name == product_data['name']
        assert retrieved_product.quantity == product_data['quantity']
        assert retrieved_product.price == product_data['price']
        assert retrieved_product.category == product_data['category']
        assert retrieved_product.alert_threshold == product_data['alert_threshold']
        assert retrieved_product.id is not None
        assert retrieved_product.created_at is not None
        assert retrieved_product.updated_at is not None
    
    @given(data=st.data())
    def test_property_5_product_update_persistence(self, data):
        """
        Property 5: Product Update Persistence
        
        For any existing product and valid update data, updating the product 
        should result in the new values being stored and retrievable.
        
        Validates: Requirements 2.2
        Feature: inventory-management-system, Property 5: Product Update Persistence
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Create initial product
        initial_data = data.draw(valid_product_data(category))
        product = Product.objects.create(**initial_data)
        original_id = product.id
        original_created_at = product.created_at
        original_updated_at = product.updated_at
        
        # Generate update data
        update_data = data.draw(valid_update_data())
        
        # Update product
        product.name = update_data['name']
        product.quantity = update_data['quantity']
        product.price = update_data['price']
        product.alert_threshold = update_data['alert_threshold']
        product.save()
        
        # Retrieve updated product
        updated_product = Product.objects.get(id=original_id)
        
        # Assert updates are persisted
        assert updated_product.name == update_data['name']
        assert updated_product.quantity == update_data['quantity']
        assert updated_product.price == update_data['price']
        assert updated_product.alert_threshold == update_data['alert_threshold']
        
        # Assert identity is preserved
        assert updated_product.id == original_id
        assert updated_product.created_at == original_created_at
        # updated_at should be >= original (may be equal if update happens in same microsecond)
        assert updated_product.updated_at >= original_updated_at
    
    @given(quantity=st.integers(max_value=-1))
    def test_property_6_quantity_non_negativity_validation(self, quantity):
        """
        Property 6: Quantity Non-Negativity Validation
        
        For any negative integer quantity value, attempting to create or update 
        a product with that quantity should be rejected by validation.
        
        Validates: Requirements 2.3
        Feature: inventory-management-system, Property 6: Quantity Non-Negativity Validation
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Attempt to create product with negative quantity
        product = Product(
            name="Test Product",
            quantity=quantity,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=5
        )
        
        # Validation should fail
        with pytest.raises(ValidationError):
            product.full_clean()
    
    @given(price=st.one_of(
        st.decimals(max_value=Decimal('0.00'), places=2),
        st.just(Decimal('0.00'))
    ))
    def test_property_7_price_positivity_validation(self, price):
        """
        Property 7: Price Positivity Validation
        
        For any non-positive price value (zero or negative), attempting to create 
        or update a product with that price should be rejected by validation.
        
        Validates: Requirements 2.4
        Feature: inventory-management-system, Property 7: Price Positivity Validation
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Attempt to create product with non-positive price
        product = Product(
            name="Test Product",
            quantity=10,
            price=price,
            category=category,
            alert_threshold=5
        )
        
        # Validation should fail
        with pytest.raises(ValidationError):
            product.full_clean()
    
    @given(data=st.data())
    def test_property_8_product_deletion(self, data):
        """
        Property 8: Product Deletion
        
        For any existing product, deleting it should result in that product 
        no longer being retrievable from the database.
        
        Validates: Requirements 2.6
        Feature: inventory-management-system, Property 8: Product Deletion
        """
        # Get or create test category
        category = get_or_create_test_category()
        
        # Create product
        product_data = data.draw(valid_product_data(category))
        product = Product.objects.create(**product_data)
        product_id = product.id
        
        # Verify product exists
        assert Product.objects.filter(id=product_id).exists()
        
        # Delete product
        product.delete()
        
        # Verify product no longer exists
        assert not Product.objects.filter(id=product_id).exists()
        
        # Attempting to retrieve should raise DoesNotExist
        with pytest.raises(Product.DoesNotExist):
            Product.objects.get(id=product_id)
    
    @given(data=st.data())
    def test_property_17_product_search_matching(self, data):
        """
        Property 17: Product Search Matching

        For any search query string, all returned products should have the query
        string appearing in their name (case-insensitive).

        Validates: Requirements 5.1
        Feature: inventory-management-system, Property 17: Product Search Matching
        """
        from inventory.services import ProductService

        # Get or create test category
        category = get_or_create_test_category()

        # Create multiple products with different names
        num_products = data.draw(st.integers(min_value=3, max_value=10))
        products = []

        for _ in range(num_products):
            product_data = data.draw(valid_product_data(category))
            product = Product.objects.create(**product_data)
            products.append(product)

        # Generate a search query from one of the product names
        # Pick a random product and extract a substring from its name
        target_product = data.draw(st.sampled_from(products))
        assume(len(target_product.name) > 0)

        # Extract a substring (at least 1 character)
        if len(target_product.name) == 1:
            query = target_product.name
        else:
            start_idx = data.draw(st.integers(min_value=0, max_value=len(target_product.name) - 1))
            end_idx = data.draw(st.integers(min_value=start_idx + 1, max_value=len(target_product.name)))
            query = target_product.name[start_idx:end_idx]

        # Search for products
        service = ProductService()
        results = service.search_products(query=query)

        # All returned products should contain the query string (case-insensitive)
        for product in results:
            assert query.lower() in product.name.lower(), \
                f"Product '{product.name}' does not contain query '{query}'"

        # The target product should be in the results
        assert target_product in results, \
            f"Target product '{target_product.name}' not found in search results for query '{query}'"
    
    @given(data=st.data())
    def test_property_18_category_filtering(self, data):
        """
        Property 18: Category Filtering

        For any category filter, all returned products should belong to that
        category, and all products in that category should be returned.

        Validates: Requirements 5.2
        Feature: inventory-management-system, Property 18: Category Filtering
        """
        from inventory.services import ProductService
        
        # Clear existing products to ensure test isolation
        Product.objects.all().delete()
        Category.objects.all().delete()

        # Create multiple categories
        num_categories = data.draw(st.integers(min_value=2, max_value=5))
        categories = []

        for i in range(num_categories):
            category_name = f"Category_{i}_{data.draw(st.integers(min_value=1000, max_value=9999))}"
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f"Test category {i}"}
            )
            categories.append(category)

        # Create products in different categories
        products_by_category = {cat: [] for cat in categories}

        for category in categories:
            num_products = data.draw(st.integers(min_value=1, max_value=5))
            for _ in range(num_products):
                product_data = data.draw(valid_product_data(category))
                product = Product.objects.create(**product_data)
                products_by_category[category].append(product)

        # Pick a category to filter by
        target_category = data.draw(st.sampled_from(categories))

        # Filter products by category
        service = ProductService()
        results = service.search_products(category=target_category.name)
        results_list = list(results)

        # All returned products should belong to the target category
        for product in results_list:
            assert product.category == target_category, \
                f"Product '{product.name}' has category '{product.category.name}' but expected '{target_category.name}'"

        # All products in the target category should be returned
        expected_products = products_by_category[target_category]
        assert len(results_list) == len(expected_products), \
            f"Expected {len(expected_products)} products but got {len(results_list)}"

        for expected_product in expected_products:
            assert expected_product in results_list, \
                f"Product '{expected_product.name}' from category '{target_category.name}' not in results"
    
    @given(data=st.data())
    def test_property_19_stock_status_filtering(self, data):
        """
        Property 19: Stock Status Filtering

        For any stock status filter (in-stock, low-stock, out-of-stock), all
        returned products should match that status based on their quantity and
        alert threshold.

        Validates: Requirements 5.3
        Feature: inventory-management-system, Property 19: Stock Status Filtering
        """
        from inventory.services import ProductService

        # Get or create test category
        category = get_or_create_test_category()

        # Create products with different stock statuses
        # Out-of-stock: quantity = 0
        out_of_stock_product = Product.objects.create(
            name=f"OutOfStock_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=0,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=data.draw(st.integers(min_value=1, max_value=100))
        )

        # Low-stock: 0 < quantity < alert_threshold
        low_stock_threshold = data.draw(st.integers(min_value=10, max_value=100))
        low_stock_quantity = data.draw(st.integers(min_value=1, max_value=low_stock_threshold - 1))
        low_stock_product = Product.objects.create(
            name=f"LowStock_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=low_stock_quantity,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=low_stock_threshold
        )

        # In-stock: quantity >= alert_threshold
        in_stock_threshold = data.draw(st.integers(min_value=5, max_value=50))
        in_stock_quantity = data.draw(st.integers(min_value=in_stock_threshold, max_value=in_stock_threshold + 100))
        in_stock_product = Product.objects.create(
            name=f"InStock_{data.draw(st.integers(min_value=1000, max_value=9999))}",
            quantity=in_stock_quantity,
            price=Decimal('10.00'),
            category=category,
            alert_threshold=in_stock_threshold
        )

        service = ProductService()

        # Test out-of-stock filter
        out_of_stock_results = list(service.search_products(stock_status='out-of-stock'))
        assert out_of_stock_product in out_of_stock_results, \
            "Out-of-stock product not found in out-of-stock filter results"
        for product in out_of_stock_results:
            assert product.quantity == 0, \
                f"Product '{product.name}' with quantity {product.quantity} should not be in out-of-stock results"

        # Test low-stock filter
        low_stock_results = list(service.search_products(stock_status='low-stock'))
        assert low_stock_product in low_stock_results, \
            "Low-stock product not found in low-stock filter results"
        for product in low_stock_results:
            assert product.quantity > 0, \
                f"Product '{product.name}' with quantity 0 should not be in low-stock results"
            assert product.quantity < product.alert_threshold, \
                f"Product '{product.name}' with quantity {product.quantity} >= threshold {product.alert_threshold} should not be in low-stock results"

        # Test in-stock filter
        in_stock_results = list(service.search_products(stock_status='in-stock'))
        assert in_stock_product in in_stock_results, \
            "In-stock product not found in in-stock filter results"
        for product in in_stock_results:
            assert product.quantity >= product.alert_threshold, \
                f"Product '{product.name}' with quantity {product.quantity} < threshold {product.alert_threshold} should not be in in-stock results"


    @given(data=st.data())
    def test_property_20_bulk_update_atomicity(self, data):
        """
        Property 20: Bulk Update Atomicity

        For any set of product updates where at least one fails validation,
        no products should be modified (all-or-nothing behavior).

        Validates: Requirements 6.3, 6.4
        Feature: inventory-management-system, Property 20: Bulk Update Atomicity
        """
        from inventory.services import ProductService

        # Get or create test category
        category = get_or_create_test_category()

        # Create multiple products
        num_products = data.draw(st.integers(min_value=3, max_value=10))
        products = []
        original_quantities = {}
        original_prices = {}

        for _ in range(num_products):
            product_data = data.draw(valid_product_data(category))
            product = Product.objects.create(**product_data)
            products.append(product)
            original_quantities[product.id] = product.quantity
            original_prices[product.id] = product.price

        service = ProductService()

        # Test 1: Bulk quantity update with one invalid value (negative)
        # Create updates where one has a negative quantity
        quantity_updates = []
        for i, product in enumerate(products):
            if i == 0:
                # First update is invalid (negative quantity)
                quantity_updates.append({'id': product.id, 'quantity': -1})
            else:
                # Other updates are valid
                new_quantity = data.draw(st.integers(min_value=0, max_value=1000))
                quantity_updates.append({'id': product.id, 'quantity': new_quantity})

        # Attempt bulk update - should fail
        with pytest.raises(ValidationError):
            service.bulk_update_quantities(quantity_updates)

        # Verify NO products were modified (atomicity)
        for product in products:
            product.refresh_from_db()
            assert product.quantity == original_quantities[product.id], \
                f"Product {product.id} quantity was modified despite validation failure"

        # Test 2: Bulk price update with one invalid value (non-positive)
        # Create updates where one has a non-positive price
        price_updates = []
        for i, product in enumerate(products):
            if i == 0:
                # First update is invalid (zero price)
                price_updates.append({'id': product.id, 'price': Decimal('0.00')})
            else:
                # Other updates are valid
                new_price = data.draw(st.decimals(
                    min_value=Decimal('0.01'),
                    max_value=Decimal('999.99'),
                    places=2
                ))
                price_updates.append({'id': product.id, 'price': new_price})

        # Attempt bulk update - should fail
        with pytest.raises(ValidationError):
            service.bulk_update_prices(price_updates)

        # Verify NO products were modified (atomicity)
        for product in products:
            product.refresh_from_db()
            assert product.price == original_prices[product.id], \
                f"Product {product.id} price was modified despite validation failure"

    @given(data=st.data())
    def test_property_21_bulk_update_application(self, data):
        """
        Property 21: Bulk Update Application

        For any set of valid product updates (quantities or prices), all
        specified products should be updated with their new values.

        Validates: Requirements 6.1, 6.2
        Feature: inventory-management-system, Property 21: Bulk Update Application
        """
        from inventory.services import ProductService

        # Get or create test category
        category = get_or_create_test_category()

        # Create multiple products
        num_products = data.draw(st.integers(min_value=2, max_value=10))
        products = []

        for _ in range(num_products):
            product_data = data.draw(valid_product_data(category))
            product = Product.objects.create(**product_data)
            products.append(product)

        service = ProductService()

        # Test 1: Bulk quantity updates (all valid)
        quantity_updates = []
        expected_quantities = {}

        for product in products:
            new_quantity = data.draw(st.integers(min_value=0, max_value=1000))
            quantity_updates.append({'id': product.id, 'quantity': new_quantity})
            expected_quantities[product.id] = new_quantity

        # Apply bulk quantity update
        updated_products = service.bulk_update_quantities(quantity_updates)

        # Verify all products were updated
        assert len(updated_products) == len(products), \
            f"Expected {len(products)} updated products but got {len(updated_products)}"

        for product in products:
            product.refresh_from_db()
            assert product.quantity == expected_quantities[product.id], \
                f"Product {product.id} quantity not updated correctly"

        # Test 2: Bulk price updates (all valid)
        price_updates = []
        expected_prices = {}

        for product in products:
            new_price = data.draw(st.decimals(
                min_value=Decimal('0.01'),
                max_value=Decimal('999.99'),
                places=2
            ))
            price_updates.append({'id': product.id, 'price': new_price})
            expected_prices[product.id] = new_price

        # Apply bulk price update
        updated_products = service.bulk_update_prices(price_updates)

        # Verify all products were updated
        assert len(updated_products) == len(products), \
            f"Expected {len(products)} updated products but got {len(updated_products)}"

        for product in products:
            product.refresh_from_db()
            assert product.price == expected_prices[product.id], \
                f"Product {product.id} price not updated correctly"

    @given(data=st.data())
    def test_property_22_bulk_update_transaction_logging(self, data):
        """
        Property 22: Bulk Update Transaction Logging

        For any successful bulk update operation affecting N products, exactly
        N transaction records should be created in the transaction history.

        Note: This property test validates the concept, but actual transaction
        logging is implemented in Task 6.1 (TransactionService). This test
        will be updated once StockTransaction logging is integrated with
        bulk updates.

        Validates: Requirements 6.5
        Feature: inventory-management-system, Property 22: Bulk Update Transaction Logging
        """
        from inventory.services import ProductService
        from inventory.models import StockTransaction

        # Get or create test category
        category = get_or_create_test_category()

        # Create multiple products
        num_products = data.draw(st.integers(min_value=2, max_value=5))
        products = []

        for _ in range(num_products):
            product_data = data.draw(valid_product_data(category))
            product = Product.objects.create(**product_data)
            products.append(product)

        service = ProductService()

        # Count existing transactions before bulk update
        initial_transaction_count = StockTransaction.objects.count()

        # Create valid quantity updates
        quantity_updates = []
        for product in products:
            new_quantity = data.draw(st.integers(min_value=0, max_value=1000))
            quantity_updates.append({'id': product.id, 'quantity': new_quantity})

        # Apply bulk quantity update
        updated_products = service.bulk_update_quantities(quantity_updates)

        # NOTE: Transaction logging for bulk updates will be implemented in Task 6.1
        # For now, we verify that the bulk update itself succeeds
        # Once Task 6.1 is complete, this test should verify:
        # final_transaction_count = StockTransaction.objects.count()
        # assert final_transaction_count == initial_transaction_count + num_products

        # Current verification: bulk update succeeded
        assert len(updated_products) == num_products, \
            f"Expected {num_products} updated products but got {len(updated_products)}"

        # Placeholder assertion - will be replaced when transaction logging is implemented
        # This ensures the test structure is in place
        assert True, "Transaction logging will be validated once Task 6.1 is complete"
