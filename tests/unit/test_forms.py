import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from inventory.forms import ProductForm, TransactionForm, BulkUpdateForm
from inventory.models import Product, Category


@pytest.mark.django_db
class TestProductForm:
    """Unit tests for ProductForm validation"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Electronics', description='Electronic items')
    
    def test_valid_product_form(self, category):
        """Test that valid product data passes validation"""
        form_data = {
            'name': 'Laptop',
            'quantity': 10,
            'price': Decimal('999.99'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_negative_quantity_rejected(self, category):
        """Test that negative quantity is rejected - Requirement 2.3"""
        form_data = {
            'name': 'Laptop',
            'quantity': -5,
            'price': Decimal('999.99'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity' in form.errors
        assert 'cannot be negative' in str(form.errors['quantity']).lower()
    
    def test_zero_quantity_accepted(self, category):
        """Test that zero quantity is accepted"""
        form_data = {
            'name': 'Laptop',
            'quantity': 0,
            'price': Decimal('999.99'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_zero_price_rejected(self, category):
        """Test that zero price is rejected - Requirement 2.4"""
        form_data = {
            'name': 'Laptop',
            'quantity': 10,
            'price': Decimal('0'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'price' in form.errors
        assert 'positive' in str(form.errors['price']).lower()
    
    def test_negative_price_rejected(self, category):
        """Test that negative price is rejected - Requirement 2.4"""
        form_data = {
            'name': 'Laptop',
            'quantity': 10,
            'price': Decimal('-50.00'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'price' in form.errors
        assert 'positive' in str(form.errors['price']).lower()
    
    def test_positive_price_accepted(self, category):
        """Test that positive price is accepted"""
        form_data = {
            'name': 'Laptop',
            'quantity': 10,
            'price': Decimal('0.01'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_negative_alert_threshold_rejected(self, category):
        """Test that negative alert threshold is rejected"""
        form_data = {
            'name': 'Laptop',
            'quantity': 10,
            'price': Decimal('999.99'),
            'category': category.id,
            'alert_threshold': -3
        }
        form = ProductForm(data=form_data)
        assert not form.is_valid()
        assert 'alert_threshold' in form.errors
        assert 'cannot be negative' in str(form.errors['alert_threshold']).lower()
    
    def test_xss_prevention_in_name(self, category):
        """Test that HTML in product name is escaped - Requirement 10.3"""
        form_data = {
            'name': '<script>alert("XSS")</script>',
            'quantity': 10,
            'price': Decimal('999.99'),
            'category': category.id,
            'alert_threshold': 5
        }
        form = ProductForm(data=form_data)
        assert form.is_valid()
        cleaned_name = form.cleaned_data['name']
        # HTML should be escaped
        assert '<script>' not in cleaned_name
        assert '&lt;script&gt;' in cleaned_name or 'script' not in cleaned_name.lower()
    
    def test_missing_required_fields(self):
        """Test that missing required fields are rejected"""
        form = ProductForm(data={})
        assert not form.is_valid()
        assert 'name' in form.errors
        assert 'quantity' in form.errors
        assert 'price' in form.errors
        assert 'category' in form.errors


@pytest.mark.django_db
class TestTransactionForm:
    """Unit tests for TransactionForm validation"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Electronics')
    
    @pytest.fixture
    def product(self, category):
        """Create a test product"""
        return Product.objects.create(
            name='Laptop',
            quantity=10,
            price=Decimal('999.99'),
            category=category,
            alert_threshold=5
        )
    
    def test_valid_purchase_transaction(self, product):
        """Test that valid purchase transaction passes validation"""
        form_data = {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': 5
        }
        form = TransactionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_valid_sale_transaction(self, product):
        """Test that valid sale transaction passes validation"""
        form_data = {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': 5
        }
        form = TransactionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_overselling_rejected(self, product):
        """Test that selling more than available quantity is rejected - Requirement 3.3"""
        form_data = {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': 15  # Product only has 10
        }
        form = TransactionForm(data=form_data)
        assert not form.is_valid()
        assert 'Insufficient inventory' in str(form.errors)
    
    def test_zero_quantity_rejected(self, product):
        """Test that zero quantity change is rejected"""
        form_data = {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': 0
        }
        form = TransactionForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity_change' in form.errors
        assert 'positive' in str(form.errors['quantity_change']).lower()
    
    def test_negative_quantity_rejected(self, product):
        """Test that negative quantity change is rejected"""
        form_data = {
            'product': product.id,
            'transaction_type': 'purchase',
            'quantity_change': -5
        }
        form = TransactionForm(data=form_data)
        assert not form.is_valid()
        assert 'quantity_change' in form.errors
        assert 'positive' in str(form.errors['quantity_change']).lower()
    
    def test_sale_at_exact_quantity(self, product):
        """Test that selling exact available quantity is allowed"""
        form_data = {
            'product': product.id,
            'transaction_type': 'sale',
            'quantity_change': 10  # Exact quantity available
        }
        form = TransactionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"


@pytest.mark.django_db
class TestBulkUpdateForm:
    """Unit tests for BulkUpdateForm validation"""
    
    @pytest.fixture
    def category(self):
        """Create a test category"""
        return Category.objects.create(name='Electronics')
    
    @pytest.fixture
    def products(self, category):
        """Create test products"""
        products = []
        for i in range(3):
            product = Product.objects.create(
                name=f'Product {i}',
                quantity=10,
                price=Decimal('100.00'),
                category=category,
                alert_threshold=5
            )
            products.append(product)
        return products
    
    def test_valid_quantity_bulk_update(self, products):
        """Test that valid bulk quantity update passes validation"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal('20')
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_valid_price_bulk_update(self, products):
        """Test that valid bulk price update passes validation"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'price',
            'product_ids': product_ids,
            'value': Decimal('150.50')
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_negative_quantity_rejected(self, products):
        """Test that negative quantity in bulk update is rejected - Requirement 6.3"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal('-5')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'value' in form.errors or '__all__' in form.errors
    
    def test_zero_price_rejected(self, products):
        """Test that zero price in bulk update is rejected - Requirement 6.3"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'price',
            'product_ids': product_ids,
            'value': Decimal('0')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'value' in form.errors or '__all__' in form.errors
    
    def test_negative_price_rejected(self, products):
        """Test that negative price in bulk update is rejected"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'price',
            'product_ids': product_ids,
            'value': Decimal('-50.00')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'value' in form.errors or '__all__' in form.errors
    
    def test_empty_product_ids_rejected(self):
        """Test that empty product IDs are rejected"""
        form_data = {
            'operation': 'quantity',
            'product_ids': '',
            'value': Decimal('20')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'product_ids' in form.errors
    
    def test_invalid_product_ids_rejected(self, products):
        """Test that invalid product IDs are rejected"""
        form_data = {
            'operation': 'quantity',
            'product_ids': '999,1000,1001',  # Non-existent IDs
            'value': Decimal('20')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'product_ids' in form.errors
    
    def test_xss_prevention_in_product_ids(self, products):
        """Test that XSS attempts in product IDs are sanitized - Requirement 10.3"""
        form_data = {
            'operation': 'quantity',
            'product_ids': '<script>alert("XSS")</script>',
            'value': Decimal('20')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        # Should fail validation due to invalid format, not cause XSS
        assert 'product_ids' in form.errors
    
    def test_fractional_quantity_rejected(self, products):
        """Test that fractional quantity is rejected"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal('10.5')
        }
        form = BulkUpdateForm(data=form_data)
        assert not form.is_valid()
        assert 'value' in form.errors
        assert 'whole number' in str(form.errors['value']).lower()
    
    def test_zero_quantity_accepted(self, products):
        """Test that zero quantity in bulk update is accepted"""
        product_ids = ','.join(str(p.id) for p in products)
        form_data = {
            'operation': 'quantity',
            'product_ids': product_ids,
            'value': Decimal('0')
        }
        form = BulkUpdateForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
