from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
from decimal import Decimal
from .models import Product, StockTransaction, Category


class ProductForm(forms.ModelForm):
    """Form for creating and updating products with validation"""
    
    class Meta:
        model = Product
        fields = ['name', 'quantity', 'price', 'category', 'alert_threshold']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quantity',
                'min': '0'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price',
                'step': '0.01',
                'min': '0.01'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter alert threshold',
                'min': '0'
            })
        }
    
    def clean_name(self):
        """Sanitize product name to prevent XSS"""
        name = self.cleaned_data.get('name')
        if name:
            # Escape HTML to prevent XSS
            name = escape(name)
        return name
    
    def clean_quantity(self):
        """Validate that quantity is non-negative integer"""
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise ValidationError('Quantity is required.')
        if quantity < 0:
            raise ValidationError('Quantity cannot be negative.')
        return quantity
    
    def clean_price(self):
        """Validate that price is positive decimal value"""
        price = self.cleaned_data.get('price')
        if price is None:
            raise ValidationError('Price is required.')
        if price <= Decimal('0'):
            raise ValidationError('Price must be a positive value.')
        return price
    
    def clean_alert_threshold(self):
        """Validate that alert threshold is non-negative"""
        threshold = self.cleaned_data.get('alert_threshold')
        if threshold is None:
            raise ValidationError('Alert threshold is required.')
        if threshold < 0:
            raise ValidationError('Alert threshold cannot be negative.')
        return threshold


class TransactionForm(forms.ModelForm):
    """Form for recording stock transactions (purchases/sales)"""
    
    class Meta:
        model = StockTransaction
        fields = ['product', 'transaction_type', 'quantity_change']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'quantity_change': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quantity',
                'min': '1'
            })
        }
    
    def clean_quantity_change(self):
        """Validate that quantity change is positive"""
        quantity_change = self.cleaned_data.get('quantity_change')
        if quantity_change is None:
            raise ValidationError('Quantity is required.')
        if quantity_change <= 0:
            raise ValidationError('Quantity must be a positive value.')
        return quantity_change
    
    def clean(self):
        """Validate transaction based on type"""
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        transaction_type = cleaned_data.get('transaction_type')
        quantity_change = cleaned_data.get('quantity_change')
        
        if product and transaction_type == 'sale' and quantity_change:
            # For sales, check if sufficient inventory exists
            if product.quantity < quantity_change:
                raise ValidationError(
                    f'Insufficient inventory. Only {product.quantity} units available.'
                )
        
        return cleaned_data


class BulkUpdateForm(forms.Form):
    """Form for bulk updating product quantities or prices"""
    
    OPERATION_CHOICES = [
        ('quantity', 'Update Quantities'),
        ('price', 'Update Prices'),
    ]
    
    operation = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Operation Type'
    )
    
    product_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        label='Product IDs'
    )
    
    value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new value',
            'step': '0.01'
        }),
        label='New Value'
    )
    
    def clean_product_ids(self):
        """Sanitize and validate product IDs"""
        product_ids_str = self.cleaned_data.get('product_ids')
        if not product_ids_str:
            raise ValidationError('No products selected.')
        
        # Sanitize input to prevent XSS
        product_ids_str = escape(product_ids_str)
        
        try:
            # Parse comma-separated IDs
            product_ids = [int(pid.strip()) for pid in product_ids_str.split(',') if pid.strip()]
        except (ValueError, AttributeError):
            raise ValidationError('Invalid product IDs format.')
        
        if not product_ids:
            raise ValidationError('No valid products selected.')
        
        # Verify all products exist
        existing_count = Product.objects.filter(id__in=product_ids).count()
        if existing_count != len(product_ids):
            raise ValidationError('Some selected products do not exist.')
        
        return product_ids
    
    def clean_value(self):
        """Validate value based on operation type"""
        value = self.cleaned_data.get('value')
        operation = self.data.get('operation')
        
        if value is None:
            raise ValidationError('Value is required.')
        
        if operation == 'quantity':
            # Quantity must be non-negative integer
            if value < 0:
                raise ValidationError('Quantity cannot be negative.')
            if value != int(value):
                raise ValidationError('Quantity must be a whole number.')
        elif operation == 'price':
            # Price must be positive
            if value <= 0:
                raise ValidationError('Price must be a positive value.')
        
        return value
    
    def clean(self):
        """Additional validation for bulk operations"""
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')
        value = cleaned_data.get('value')
        
        # Ensure operation and value are compatible
        if operation and value is not None:
            if operation == 'quantity' and value < 0:
                raise ValidationError('Quantity cannot be negative.')
            elif operation == 'price' and value <= 0:
                raise ValidationError('Price must be positive.')
        
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Form for creating and updating categories"""

    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category description (optional)',
                'rows': 3
            })
        }

    def clean_name(self):
        """Sanitize category name to prevent XSS"""
        name = self.cleaned_data.get('name')
        if name:
            # Escape HTML to prevent XSS
            name = escape(name)
        return name

    def clean_description(self):
        """Sanitize description to prevent XSS"""
        description = self.cleaned_data.get('description')
        if description:
            # Escape HTML to prevent XSS
            description = escape(description)
        return description




class CategoryForm(forms.ModelForm):
    """Form for creating and updating categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category description (optional)',
                'rows': 3
            })
        }
    
    def clean_name(self):
        """Sanitize category name to prevent XSS"""
        name = self.cleaned_data.get('name')
        if name:
            # Escape HTML to prevent XSS
            name = escape(name)
        return name
    
    def clean_description(self):
        """Sanitize description to prevent XSS"""
        description = self.cleaned_data.get('description')
        if description:
            # Escape HTML to prevent XSS
            description = escape(description)
        return description
