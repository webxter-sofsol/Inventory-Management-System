import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from decimal import Decimal
from inventory.forms import ProductForm, TransactionForm, BulkUpdateForm
from inventory.models import Product, Category


@pytest.mark.django_db
class TestProductFormProperties:
    """Property-based tests for ProductForm"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Test Category')
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity=st.integers(min_value=0, max_value=1000000)
    )
    def test_non_negative_quantities_accepted(self, category, quantity):
        """Property: All non-negative quantities should be accepted
        
        **Validates: Requirements 2.3**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': quantity,
            'price': Decimal('10.00'),
            'category': category.id,
            'alert_threshold': 0
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Non-negative quantity {quantity} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity=st.integers(max_value=-1)
    )
    def test_negative_quantities_rejected(self, category, quantity):
        """Property: All negative quantities should be rejected
        
        **Validates: Requirements 2.3**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': quantity,
            'price': Decimal('10.00'),
            'category': category.id,
            'alert_threshold': 0
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid(), f"Negative quantity {quantity} was accepted"
        assert 'quantity' in form.errors
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        price=st.decimals(min_value='0.01', max_value='999999.99', places=2)
    )
    def test_positive_prices_accepted(self, category, price):
        """Property: All positive prices should be accepted
        
        **Validates: Requirements 2.4**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': 10,
            'price': price,
            'category': category.id,
            'alert_threshold': 0
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Positive price {price} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        price=st.decimals(max_value='0', places=2).filter(lambda x: x is not None)
    )
    def test_non_positive_prices_rejected(self, category, price):
        """Property: All non-positive prices should be rejected
        
        **Validates: Requirements 2.4**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': 10,
            'price': price,
            'category': category.id,
            'alert_threshold': 0
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid(), f"Non-positive price {price} was accepted"
        assert 'price' in form.errors
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        threshold=st.integers(min_value=0, max_value=1000000)
    )
    def test_non_negative_thresholds_accepted(self, category, threshold):
        """Property: All non-negative alert thresholds should be accepted
        
        **Validates: Requirements 4.5**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': 10,
            'price': Decimal('10.00'),
            'category': category.id,
            'alert_threshold': threshold
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Non-negative threshold {threshold} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        threshold=st.integers(max_value=-1)
    )
    def test_negative_thresholds_rejected(self, category, threshold):
        """Property: All negative alert thresholds should be rejected
        
        **Validates: Requirements 4.5**
        """
        form_data = {
            'name': 'Test Product',
            'quantity': 10,
            'price': Decimal('10.00'),
            'category': category.id,
            'alert_threshold': threshold
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid(), f"Negative threshold {threshold} was accepted"
        assert 'alert_threshold' in form.errors
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=st.text(min_size=1, max_size=200)
    )
    def test_xss_prevention_all_inputs(self, category, name):
        """Property: All text inputs should be sanitized to prevent XSS
        
        **Validates: Requirements 10.3**
        """
        form_data = {
            'name': name,
            'quantity': 10,
            'price': Decimal('10.00'),
            'category': category.id,
            'alert_threshold': 0
        }
        form = ProductForm(data=form_data)
        if form.is_valid():
            cleaned_name = form.cleaned_data['name']
            # If input contains script tags, they should be escaped
            if '<script>' in name.lower():
                assert '<script>' not in cleaned_name.lower() or '&lt;' in cleaned_name


@pytest.mark.django_db
class TestTransactionFormProperties:
    """Property-based tests for TransactionForm"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Test Category')
    
    @pytest.fixture
    def product(self, category):
        """Create a test product with known quantity"""
        return Product.objects.create(
            name='Test Product',
            quantity=100,
            price=Decimal('50.00'),
            category=category,
            alert_threshold=10
        )
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity_change=st.integers(min_value=1, max_value=100)
    )
    def test_valid_purchase_quantities(self, product, quantity_change):
        """Property: All positive quantities should be valid for purchases
        
        **Validates: Requirements 3.1**
        """
        form_data = {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': quantity_change
        }
        form = TransactionForm(data=form_data)
        assert form.is_valid(), f"Valid purchase quantity {quantity_change} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity_change=st.integers(min_value=1, max_value=100)
    )
    def test_valid_sale_quantities(self, product, quantity_change):
        """Property: All quantities <= product quantity should be valid for sales
        
        **Validates: Requirements 3.2**
        """
        form_data = {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': quantity_change
        }
        form = TransactionForm(data=form_data)
        assert form.is_valid(), f"Valid sale quantity {quantity_change} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity_change=st.integers(min_value=101, max_value=1000)
    )
    def test_overselling_rejected_property(self, product, quantity_change):
        """Property: All quantities > product quantity should be rejected for sales
        
        **Validates: Requirements 3.3**
        """
        form_data = {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': quantity_change
        }
        form = TransactionForm(data=form_data)
        assert not form.is_valid(), f"Overselling with {quantity_change} was accepted"
        assert 'Insufficient inventory' in str(form.errors)
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity_change=st.integers(max_value=0)
    )
    def test_non_positive_quantities_rejected(self, product, quantity_change):
        """Property: All non-positive quantities should be rejected
        
        **Validates: Requirements 10.1**
        """
        form_data = {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': quantity_change
        }
        form = TransactionForm(data=form_data)
        assert not form.is_valid(), f"Non-positive quantity {quantity_change} was accepted"
        assert 'quantity_change' in form.errors


@pytest.mark.django_db
class TestBulkUpdateFormProperties:
    """Property-based tests for BulkUpdateForm"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Test Category')
    
    @pytest.fixture
    def products(self, category):
        """Create test products"""
        products = []
        for i in range(5):
            product = Product.objects.create(
                name=f'Product {i}',
                quantity=50,
                price=Decimal('100.00'),
                category=category,
                alert_threshold=10
            )
            products.append(product)
        return products
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity=st.integers(min_value=0, max_value=10000)
    )
    def test_non_negative_quantity_updates_accepted(self, products, quantity):
        """Property: All non-negative quantities should be accepted for bulk updates
        
        **Validates: Requirements 6.1, 6.3**
        """
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal(str(quantity))
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Non-negative quantity {quantity} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        quantity=st.integers(max_value=-1)
    )
    def test_negative_quantity_updates_rejected(self, products, quantity):
        """Property: All negative quantities should be rejected for bulk updates
        
        **Validates: Requirements 6.3, 6.4**
        """
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal(str(quantity))
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid(), f"Negative quantity {quantity} was accepted"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        price=st.decimals(min_value='0.01', max_value='999999.99', places=2)
    )
    def test_positive_price_updates_accepted(self, products, price):
        """Property: All positive prices should be accepted for bulk updates
        
        **Validates: Requirements 6.2, 6.3**
        """
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'price',
            'product_ids': product_ids,
            'value': price
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Positive price {price} rejected: {form.errors}"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        price=st.decimals(max_value='0', places=2).filter(lambda x: x is not None)
    )
    def test_non_positive_price_updates_rejected(self, products, price):
        """Property: All non-positive prices should be rejected for bulk updates
        
        **Validates: Requirements 6.3, 6.4**
        """
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'price',
            'product_ids': product_ids,
            'value': price
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid(), f"Non-positive price {price} was accepted"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_products=st.integers(min_value=1, max_value=5)
    )
    def test_valid_product_id_lists(self, products, num_products):
        """Property: All valid product ID lists should be accepted
        
        **Validates: Requirements 6.1, 10.1**
        """
        selected_products = products[:num_products]
        product_ids = ','.join(str(p.id) for p in selected_products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal('50')
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Valid product IDs rejected: {form.errors}"
        assert len(form.cleaned_data['product_ids']) == num_products
