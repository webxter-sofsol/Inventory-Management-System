"""
Property-based tests for Transaction processing

Feature: inventory-management-system

These tests validate universal correctness properties using Hypothesis.
Each property should hold true for all valid inputs.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from hypothesis import given, strategies as st, assume
from django.core.exceptions import ValidationError
from django.utils import timezone

from inventory.models import Product, Category, StockTransaction
from inventory.services import TransactionService, InsufficientInventoryError
from accounts.models import CustomUser


# Hypothesis strategies for generating test data
@st.composite
def valid_product_for_transaction(draw):
    """Generate a valid product with sufficient stock for testing"""
    category, _ = Category.objects.get_or_create(
        name="Test Category",
        defaults={'description': "Test Description"}
    )
    
    quantity = draw(st.integers(min_value=10, max_value=1000))
    
    product = Product.objects.create(
        name=draw(st.text(
            min_size=1,
            max_size=200,
            alphabet=st.characters(
                blacklist_categories=('Cs',),
                blacklist_characters=['\x00']
            )
        )),
        quantity=quantity,
        price=draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999.99'), places=2)),
        category=category,
        alert_threshold=draw(st.integers(min_value=0, max_value=quantity))
    )
    
    return product


def get_or_create_test_user():
    """Get or create a test user for transaction tests"""
    user, _ = CustomUser.objects.get_or_create(
        email="test@example.com",
        defaults={'password': 'testpass123'}
    )
    return user


@pytest.mark.django_db
@pytest.mark.property
class TestTransactionProperties:
    """Property-based tests for transaction processing correctness"""
    
    @given(data=st.data())
    def test_property_9_purchase_increases_quantity(self, data):
        """
        Property 9: Purchase Increases Quantity
        
        For any product and positive purchase quantity, recording a purchase
        transaction should increase the product's quantity by exactly the
        purchase amount.
        
        Validates: Requirements 3.1
        Feature: inventory-management-system, Property 9: Purchase Increases Quantity
        """
        # Create product and user
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Record initial quantity
        initial_quantity = product.quantity
        
        # Generate purchase quantity
        purchase_quantity = data.draw(st.integers(min_value=1, max_value=1000))
        
        # Record purchase
        service = TransactionService()
        transaction = service.record_purchase(
            product_id=product.id,
            quantity=purchase_quantity,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        
        # Assert quantity increased by exactly the purchase amount
        assert product.quantity == initial_quantity + purchase_quantity, \
            f"Expected quantity {initial_quantity + purchase_quantity} but got {product.quantity}"
        
        # Assert transaction was created
        assert transaction is not None
        assert transaction.transaction_type == 'purchase'
        assert transaction.quantity_change == purchase_quantity
    
    @given(data=st.data())
    def test_property_10_sale_decreases_quantity(self, data):
        """
        Property 10: Sale Decreases Quantity
        
        For any product with sufficient stock and positive sale quantity,
        recording a sale transaction should decrease the product's quantity
        by exactly the sale amount.
        
        Validates: Requirements 3.2
        Feature: inventory-management-system, Property 10: Sale Decreases Quantity
        """
        # Create product with sufficient stock
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Record initial quantity
        initial_quantity = product.quantity
        
        # Generate sale quantity (ensure it doesn't exceed available stock)
        sale_quantity = data.draw(st.integers(min_value=1, max_value=initial_quantity))
        
        # Record sale
        service = TransactionService()
        transaction = service.record_sale(
            product_id=product.id,
            quantity=sale_quantity,
            user_id=user.id
        )
        
        # Refresh product from database
        product.refresh_from_db()
        
        # Assert quantity decreased by exactly the sale amount
        assert product.quantity == initial_quantity - sale_quantity, \
            f"Expected quantity {initial_quantity - sale_quantity} but got {product.quantity}"
        
        # Assert transaction was created
        assert transaction is not None
        assert transaction.transaction_type == 'sale'
        assert transaction.quantity_change == -sale_quantity
    
    @given(data=st.data())
    def test_property_11_overselling_prevention(self, data):
        """
        Property 11: Overselling Prevention
        
        For any product and sale quantity that exceeds the product's current
        quantity, attempting to record the sale should be rejected and the
        product quantity should remain unchanged.
        
        Validates: Requirements 3.3
        Feature: inventory-management-system, Property 11: Overselling Prevention
        """
        # Create product
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Record initial quantity
        initial_quantity = product.quantity
        
        # Generate sale quantity that exceeds available stock
        sale_quantity = data.draw(st.integers(min_value=initial_quantity + 1, max_value=initial_quantity + 1000))
        
        # Attempt to record sale - should raise InsufficientInventoryError
        service = TransactionService()
        with pytest.raises(InsufficientInventoryError):
            service.record_sale(
                product_id=product.id,
                quantity=sale_quantity,
                user_id=user.id
            )
        
        # Refresh product from database
        product.refresh_from_db()
        
        # Assert quantity remained unchanged
        assert product.quantity == initial_quantity, \
            f"Product quantity changed from {initial_quantity} to {product.quantity} despite overselling prevention"
        
        # Assert no transaction was created
        transaction_count = StockTransaction.objects.filter(
            product=product,
            transaction_type='sale',
            quantity_change=-sale_quantity
        ).count()
        assert transaction_count == 0, \
            "Transaction was created despite overselling prevention"
    
    @given(data=st.data())
    def test_property_12_transaction_logging_completeness(self, data):
        """
        Property 12: Transaction Logging Completeness
        
        For any completed stock transaction (purchase or sale), a transaction
        record should be created in the transaction history containing timestamp,
        product reference, transaction type, quantity change, and user identifier.
        
        Validates: Requirements 3.4, 3.5, 8.1
        Feature: inventory-management-system, Property 12: Transaction Logging Completeness
        """
        # Create product and user
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Randomly choose transaction type
        transaction_type = data.draw(st.sampled_from(['purchase', 'sale']))
        
        service = TransactionService()
        
        if transaction_type == 'purchase':
            quantity = data.draw(st.integers(min_value=1, max_value=1000))
            transaction = service.record_purchase(
                product_id=product.id,
                quantity=quantity,
                user_id=user.id
            )
            expected_quantity_change = quantity
        else:  # sale
            # Ensure sale quantity doesn't exceed stock
            quantity = data.draw(st.integers(min_value=1, max_value=product.quantity))
            transaction = service.record_sale(
                product_id=product.id,
                quantity=quantity,
                user_id=user.id
            )
            expected_quantity_change = -quantity
        
        # Verify transaction record exists and has all required fields
        assert transaction is not None, "Transaction record was not created"
        
        # Verify timestamp
        assert transaction.timestamp is not None, "Transaction timestamp is missing"
        assert isinstance(transaction.timestamp, type(timezone.now())), \
            "Transaction timestamp is not a datetime object"
        
        # Verify product reference
        assert transaction.product == product, \
            f"Transaction product reference incorrect: expected {product.id}, got {transaction.product.id}"
        
        # Verify transaction type
        assert transaction.transaction_type == transaction_type, \
            f"Transaction type incorrect: expected {transaction_type}, got {transaction.transaction_type}"
        
        # Verify quantity change
        assert transaction.quantity_change == expected_quantity_change, \
            f"Quantity change incorrect: expected {expected_quantity_change}, got {transaction.quantity_change}"
        
        # Verify user identifier
        assert transaction.user == user, \
            f"Transaction user reference incorrect: expected {user.id}, got {transaction.user.id if transaction.user else None}"
        
        # Verify transaction is retrievable from history
        history = StockTransaction.objects.filter(id=transaction.id)
        assert history.exists(), "Transaction not found in transaction history"
    
    @given(data=st.data())
    def test_property_25_transaction_history_ordering(self, data):
        """
        Property 25: Transaction History Ordering
        
        For any transaction history query, results should be ordered by
        timestamp in descending order (most recent first).
        
        Validates: Requirements 8.2
        Feature: inventory-management-system, Property 25: Transaction History Ordering
        """
        # Create product and user
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Create multiple transactions
        num_transactions = data.draw(st.integers(min_value=3, max_value=10))
        service = TransactionService()
        
        for _ in range(num_transactions):
            # Alternate between purchases and sales
            transaction_type = data.draw(st.sampled_from(['purchase', 'sale']))
            
            if transaction_type == 'purchase':
                quantity = data.draw(st.integers(min_value=1, max_value=100))
                service.record_purchase(
                    product_id=product.id,
                    quantity=quantity,
                    user_id=user.id
                )
            else:
                # Refresh product to get current quantity
                product.refresh_from_db()
                if product.quantity > 0:
                    quantity = data.draw(st.integers(min_value=1, max_value=min(product.quantity, 10)))
                    service.record_sale(
                        product_id=product.id,
                        quantity=quantity,
                        user_id=user.id
                    )
        
        # Get transaction history
        history = service.get_transaction_history()
        history_list = list(history)
        
        # Verify ordering (most recent first)
        for i in range(len(history_list) - 1):
            current_timestamp = history_list[i].timestamp
            next_timestamp = history_list[i + 1].timestamp
            
            assert current_timestamp >= next_timestamp, \
                f"Transaction history not ordered correctly: " \
                f"transaction at index {i} ({current_timestamp}) is older than " \
                f"transaction at index {i + 1} ({next_timestamp})"
    
    @given(data=st.data())
    def test_property_26_transaction_history_filtering(self, data):
        """
        Property 26: Transaction History Filtering
        
        For any combination of filters (date range, product, transaction type),
        all returned transactions should match all specified filter criteria,
        and all matching transactions should be returned.
        
        Validates: Requirements 8.3, 8.4, 8.5
        Feature: inventory-management-system, Property 26: Transaction History Filtering
        """
        # Clear existing transactions for test isolation
        StockTransaction.objects.all().delete()
        
        # Create multiple products
        category, _ = Category.objects.get_or_create(
            name="Test Category",
            defaults={'description': "Test Description"}
        )
        
        num_products = data.draw(st.integers(min_value=2, max_value=4))
        products = []
        
        for i in range(num_products):
            product = Product.objects.create(
                name=f"Product_{i}_{data.draw(st.integers(min_value=1000, max_value=9999))}",
                quantity=data.draw(st.integers(min_value=100, max_value=1000)),
                price=Decimal('10.00'),
                category=category,
                alert_threshold=10
            )
            products.append(product)
        
        user = get_or_create_test_user()
        service = TransactionService()
        
        # Create transactions for different products and types
        target_product = data.draw(st.sampled_from(products))
        
        for product in products:
            # Create both purchase and sale transactions
            service.record_purchase(
                product_id=product.id,
                quantity=data.draw(st.integers(min_value=1, max_value=50)),
                user_id=user.id
            )
            
            product.refresh_from_db()
            if product.quantity > 0:
                service.record_sale(
                    product_id=product.id,
                    quantity=data.draw(st.integers(min_value=1, max_value=min(product.quantity, 10))),
                    user_id=user.id
                )
        
        # Test 1: Filter by product
        product_filtered = service.get_transaction_history(product_id=target_product.id)
        for transaction in product_filtered:
            assert transaction.product == target_product, \
                f"Transaction for product {transaction.product.id} found when filtering for product {target_product.id}"
        
        # Verify all transactions for target product are included
        expected_count = StockTransaction.objects.filter(product=target_product).count()
        assert product_filtered.count() == expected_count, \
            f"Expected {expected_count} transactions for product {target_product.id} but got {product_filtered.count()}"
        
        # Test 2: Filter by transaction type
        transaction_type = data.draw(st.sampled_from(['purchase', 'sale']))
        type_filtered = service.get_transaction_history(transaction_type=transaction_type)
        for transaction in type_filtered:
            assert transaction.transaction_type == transaction_type, \
                f"Transaction type {transaction.transaction_type} found when filtering for {transaction_type}"
        
        # Test 3: Filter by date range
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # All transactions should be from today
        date_filtered = service.get_transaction_history(start_date=today, end_date=tomorrow)
        for transaction in date_filtered:
            transaction_date = transaction.timestamp.date()
            assert yesterday < transaction_date <= tomorrow, \
                f"Transaction from {transaction_date} found when filtering for {today} to {tomorrow}"
        
        # Test 4: Combined filters (product + type)
        combined_filtered = service.get_transaction_history(
            product_id=target_product.id,
            transaction_type=transaction_type
        )
        for transaction in combined_filtered:
            assert transaction.product == target_product, \
                f"Wrong product in combined filter results"
            assert transaction.transaction_type == transaction_type, \
                f"Wrong transaction type in combined filter results"
    
    @given(data=st.data())
    def test_property_27_transaction_record_completeness(self, data):
        """
        Property 27: Transaction Record Completeness
        
        For any transaction in the history, it should contain all required
        fields: timestamp, product name, transaction type, quantity change,
        and admin identifier.
        
        Validates: Requirements 8.6
        Feature: inventory-management-system, Property 27: Transaction Record Completeness
        """
        # Create product and user
        product = data.draw(valid_product_for_transaction())
        user = get_or_create_test_user()
        
        # Create a transaction
        transaction_type = data.draw(st.sampled_from(['purchase', 'sale']))
        service = TransactionService()
        
        if transaction_type == 'purchase':
            quantity = data.draw(st.integers(min_value=1, max_value=100))
            transaction = service.record_purchase(
                product_id=product.id,
                quantity=quantity,
                user_id=user.id
            )
        else:
            quantity = data.draw(st.integers(min_value=1, max_value=product.quantity))
            transaction = service.record_sale(
                product_id=product.id,
                quantity=quantity,
                user_id=user.id
            )
        
        # Retrieve transaction from history
        history = service.get_transaction_history()
        retrieved_transaction = history.filter(id=transaction.id).first()
        
        assert retrieved_transaction is not None, "Transaction not found in history"
        
        # Verify all required fields are present and valid
        
        # 1. Timestamp
        assert retrieved_transaction.timestamp is not None, \
            "Transaction timestamp is missing"
        assert isinstance(retrieved_transaction.timestamp, type(timezone.now())), \
            "Transaction timestamp is not a datetime object"
        
        # 2. Product name (accessible through product relationship)
        assert retrieved_transaction.product is not None, \
            "Transaction product reference is missing"
        assert retrieved_transaction.product.name is not None, \
            "Product name is missing"
        assert len(retrieved_transaction.product.name) > 0, \
            "Product name is empty"
        
        # 3. Transaction type
        assert retrieved_transaction.transaction_type is not None, \
            "Transaction type is missing"
        assert retrieved_transaction.transaction_type in ['purchase', 'sale'], \
            f"Invalid transaction type: {retrieved_transaction.transaction_type}"
        
        # 4. Quantity change
        assert retrieved_transaction.quantity_change is not None, \
            "Quantity change is missing"
        assert isinstance(retrieved_transaction.quantity_change, int), \
            "Quantity change is not an integer"
        if transaction_type == 'purchase':
            assert retrieved_transaction.quantity_change > 0, \
                "Purchase transaction should have positive quantity change"
        else:
            assert retrieved_transaction.quantity_change < 0, \
                "Sale transaction should have negative quantity change"
        
        # 5. Admin/User identifier
        assert retrieved_transaction.user is not None, \
            "Transaction user reference is missing"
        assert retrieved_transaction.user.id == user.id, \
            f"Transaction user ID mismatch: expected {user.id}, got {retrieved_transaction.user.id}"
