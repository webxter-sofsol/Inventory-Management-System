"""
Business logic layer for inventory management operations.

This module contains service classes that encapsulate business logic
and provide a clean interface for product and transaction operations.
"""

from decimal import Decimal
from typing import List, Dict, Optional
from datetime import date
from django.db import transaction
from django.db.models import QuerySet, Q, F
from django.core.exceptions import ValidationError
from .models import Product, Category, StockTransaction


class InsufficientInventoryError(Exception):
    """Raised when attempting to sell more inventory than available."""
    pass


class ProductService:
    """Business logic for product operations."""
    
    def create_product(
        self,
        name: str,
        quantity: int,
        price: Decimal,
        category: Category,
        alert_threshold: int
    ) -> Product:
        """
        Create and validate new product.
        
        Args:
            name: Product name
            quantity: Initial stock quantity (must be non-negative)
            price: Product price (must be positive)
            category: Product category
            alert_threshold: Low stock alert threshold (must be non-negative)
        
        Returns:
            Created Product instance
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate quantity
        if quantity < 0:
            raise ValidationError("Quantity cannot be negative")
        
        # Validate price
        if price <= 0:
            raise ValidationError("Price must be positive")
        
        # Validate alert_threshold
        if alert_threshold < 0:
            raise ValidationError("Alert threshold cannot be negative")
        
        # Create product
        product = Product.objects.create(
            name=name,
            quantity=quantity,
            price=price,
            category=category,
            alert_threshold=alert_threshold
        )
        
        return product
    
    def update_product(self, product_id: int, **kwargs) -> Product:
        """
        Update product with validation.
        
        Args:
            product_id: ID of product to update
            **kwargs: Fields to update (name, quantity, price, category, alert_threshold)
        
        Returns:
            Updated Product instance
        
        Raises:
            Product.DoesNotExist: If product not found
            ValidationError: If validation fails
        """
        product = Product.objects.get(id=product_id)
        
        # Validate quantity if provided
        if 'quantity' in kwargs:
            if kwargs['quantity'] < 0:
                raise ValidationError("Quantity cannot be negative")
        
        # Validate price if provided
        if 'price' in kwargs:
            if kwargs['price'] <= 0:
                raise ValidationError("Price must be positive")
        
        # Validate alert_threshold if provided
        if 'alert_threshold' in kwargs:
            if kwargs['alert_threshold'] < 0:
                raise ValidationError("Alert threshold cannot be negative")
        
        # Update fields
        for field, value in kwargs.items():
            if hasattr(product, field):
                setattr(product, field, value)
        
        product.save()
        return product
    
    def delete_product(self, product_id: int) -> None:
        """
        Delete product from inventory.
        
        Args:
            product_id: ID of product to delete
        
        Raises:
            Product.DoesNotExist: If product not found
        """
        product = Product.objects.get(id=product_id)
        product.delete()
    
    def search_products(
        self,
        user=None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        stock_status: Optional[str] = None
    ) -> QuerySet:
        """
        Search and filter products scoped to a specific user.
        """
        products = Product.objects.all()

        # Scope to user
        if user is not None:
            products = products.filter(user=user)

        # Filter by search query (name)
        if query:
            products = products.filter(Q(name__icontains=query))
        
        # Filter by category
        if category:
            products = products.filter(category__name=category)
        
        # Filter by stock status
        if stock_status:
            if stock_status == 'out-of-stock':
                products = products.filter(quantity=0)
            elif stock_status == 'low-stock':
                products = products.filter(
                    quantity__gt=0,
                    quantity__lt=F('alert_threshold')
                )
            elif stock_status == 'in-stock':
                products = products.filter(quantity__gte=F('alert_threshold'))
        
        return products
    
    @transaction.atomic
    def bulk_update_quantities(self, updates: List[Dict]) -> List[Product]:
        """
        Update multiple product quantities atomically.
        
        All updates succeed or all fail (all-or-nothing).
        
        Args:
            updates: List of dicts with 'id' and 'quantity' keys
                Example: [{'id': 1, 'quantity': 100}, {'id': 2, 'quantity': 50}]
        
        Returns:
            List of updated Product instances
        
        Raises:
            ValidationError: If any validation fails (no changes applied)
            Product.DoesNotExist: If any product not found (no changes applied)
        """
        # Validate all updates first (before making any changes)
        products_to_update = []
        
        for update in updates:
            product_id = update.get('id')
            quantity = update.get('quantity')
            
            if product_id is None:
                raise ValidationError("Product ID is required for each update")
            
            if quantity is None:
                raise ValidationError(f"Quantity is required for product {product_id}")
            
            if quantity < 0:
                raise ValidationError(
                    f"Quantity cannot be negative for product {product_id}"
                )
            
            # Fetch product (will raise DoesNotExist if not found)
            product = Product.objects.select_for_update().get(id=product_id)
            products_to_update.append((product, quantity))
        
        # All validations passed, apply updates
        updated_products = []
        for product, quantity in products_to_update:
            product.quantity = quantity
            product.save()
            updated_products.append(product)
        
        return updated_products
    
    @transaction.atomic
    def bulk_update_prices(self, updates: List[Dict]) -> List[Product]:
        """
        Update multiple product prices atomically.
        
        All updates succeed or all fail (all-or-nothing).
        
        Args:
            updates: List of dicts with 'id' and 'price' keys
                Example: [{'id': 1, 'price': Decimal('19.99')}, {'id': 2, 'price': Decimal('29.99')}]
        
        Returns:
            List of updated Product instances
        
        Raises:
            ValidationError: If any validation fails (no changes applied)
            Product.DoesNotExist: If any product not found (no changes applied)
        """
        # Validate all updates first (before making any changes)
        products_to_update = []
        
        for update in updates:
            product_id = update.get('id')
            price = update.get('price')
            
            if product_id is None:
                raise ValidationError("Product ID is required for each update")
            
            if price is None:
                raise ValidationError(f"Price is required for product {product_id}")
            
            # Convert to Decimal if needed
            if not isinstance(price, Decimal):
                try:
                    price = Decimal(str(price))
                except (ValueError, TypeError, Exception):
                    raise ValidationError(
                        f"Invalid price format for product {product_id}"
                    )
            
            if price <= 0:
                raise ValidationError(
                    f"Price must be positive for product {product_id}"
                )
            
            # Fetch product (will raise DoesNotExist if not found)
            product = Product.objects.select_for_update().get(id=product_id)
            products_to_update.append((product, price))
        
        # All validations passed, apply updates
        updated_products = []
        for product, price in products_to_update:
            product.price = price
            product.save()
            updated_products.append(product)
        
        return updated_products



class TransactionService:
    """Business logic for transaction processing."""
    
    @transaction.atomic
    def record_purchase(
        self,
        product_id: int,
        quantity: int,
        user_id: int
    ) -> StockTransaction:
        """
        Record purchase and increase stock.
        
        Args:
            product_id: ID of product to purchase
            quantity: Quantity to add (must be positive)
            user_id: ID of user recording the transaction
        
        Returns:
            Created StockTransaction instance
        
        Raises:
            Product.DoesNotExist: If product not found
            ValidationError: If validation fails
        """
        # Validate quantity
        if quantity <= 0:
            raise ValidationError("Purchase quantity must be positive")
        
        # Lock product row for update
        product = Product.objects.select_for_update().get(id=product_id)
        
        # Increase product quantity
        product.quantity += quantity
        product.save()
        
        # Create transaction record
        stock_transaction = StockTransaction.objects.create(
            product=product,
            user_id=user_id,
            transaction_type='purchase',
            quantity_change=quantity
        )
        
        # Check if alert should be resolved (quantity increased)
        AlertService.resolve_alert(product)
        
        return stock_transaction
    
    @transaction.atomic
    def record_sale(
        self,
        product_id: int,
        quantity: int,
        user_id: int
    ) -> StockTransaction:
        """
        Record sale and decrease stock, validate sufficient inventory.
        
        Args:
            product_id: ID of product to sell
            quantity: Quantity to sell (must be positive)
            user_id: ID of user recording the transaction
        
        Returns:
            Created StockTransaction instance
        
        Raises:
            Product.DoesNotExist: If product not found
            ValidationError: If validation fails
            InsufficientInventoryError: If insufficient stock available
        """
        # Validate quantity
        if quantity <= 0:
            raise ValidationError("Sale quantity must be positive")
        
        # Lock product row for update
        product = Product.objects.select_for_update().get(id=product_id)
        
        # Check for sufficient inventory (overselling prevention)
        if product.quantity < quantity:
            raise InsufficientInventoryError(
                f"Cannot sell {quantity} units of {product.name}. "
                f"Only {product.quantity} available."
            )
        
        # Decrease product quantity
        product.quantity -= quantity
        product.save()
        
        # Create transaction record
        stock_transaction = StockTransaction.objects.create(
            product=product,
            user_id=user_id,
            transaction_type='sale',
            quantity_change=-quantity
        )
        
        # Check if alert should be created (quantity decreased)
        AlertService.check_and_create_alert(product)
        
        return stock_transaction
    
    def get_transaction_history(
        self,
        user=None,
        product_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[str] = None
    ) -> QuerySet:
        """
        Retrieve filtered transaction history scoped to a user.
        """
        transactions = StockTransaction.objects.all()

        # Scope to user's products
        if user is not None:
            transactions = transactions.filter(product__user=user)

        if product_id is not None:
            transactions = transactions.filter(product_id=product_id)
        
        if start_date is not None:
            transactions = transactions.filter(timestamp__date__gte=start_date)
        
        if end_date is not None:
            transactions = transactions.filter(timestamp__date__lte=end_date)
        
        if transaction_type is not None:
            if transaction_type not in ['purchase', 'sale']:
                raise ValidationError("Transaction type must be 'purchase' or 'sale'")
            transactions = transactions.filter(transaction_type=transaction_type)
        
        return transactions



class AlertService:
    """Business logic for alert management."""

    @staticmethod
    def check_and_create_alert(product: Product) -> Optional['LowStockAlert']:
        """
        Check if product is below threshold and create alert if needed.

        Args:
            product: Product instance to check

        Returns:
            LowStockAlert instance if alert was created, None otherwise
        """
        from .models import LowStockAlert

        # Check if product quantity is below alert threshold
        if product.quantity < product.alert_threshold:
            # Check if alert already exists
            alert, created = LowStockAlert.objects.get_or_create(
                product=product,
                defaults={'is_active': True}
            )

            # If alert existed but was inactive, reactivate it
            if not created and not alert.is_active:
                alert.is_active = True
                alert.save()

            return alert

        return None

    @staticmethod
    def resolve_alert(product: Product) -> None:
        """
        Remove alert when stock rises above threshold.

        Args:
            product: Product instance to check
        """
        from .models import LowStockAlert

        # Check if product quantity is at or above alert threshold
        if product.quantity >= product.alert_threshold:
            # Delete any existing alert for this product
            try:
                alert = LowStockAlert.objects.get(product=product)
                alert.delete()
            except LowStockAlert.DoesNotExist:
                # No alert exists, nothing to do
                pass

    @staticmethod
    def get_active_alerts() -> QuerySet:
        """
        Retrieve all active low-stock alerts for dashboard display.

        Returns:
            QuerySet of active LowStockAlert instances with related products
        """
        from .models import LowStockAlert

        return LowStockAlert.objects.filter(
            is_active=True
        ).select_related('product', 'product__category').order_by('created_at')




class AlertService:
    """Business logic for alert management."""
    
    @staticmethod
    def check_and_create_alert(product: Product) -> Optional['LowStockAlert']:
        """
        Check if product is below threshold and create alert if needed.
        
        Args:
            product: Product instance to check
        
        Returns:
            LowStockAlert instance if alert was created, None otherwise
        """
        from .models import LowStockAlert
        
        # Check if product quantity is below alert threshold
        if product.quantity < product.alert_threshold:
            # Check if alert already exists
            alert, created = LowStockAlert.objects.get_or_create(
                product=product,
                defaults={'is_active': True}
            )
            
            # If alert existed but was inactive, reactivate it
            if not created and not alert.is_active:
                alert.is_active = True
                alert.save()
            
            return alert
        
        return None
    
    @staticmethod
    def resolve_alert(product: Product) -> None:
        """
        Remove alert when stock rises above threshold.
        
        Args:
            product: Product instance to check
        """
        from .models import LowStockAlert
        
        # Check if product quantity is at or above alert threshold
        if product.quantity >= product.alert_threshold:
            # Delete any existing alert for this product
            try:
                alert = LowStockAlert.objects.get(product=product)
                alert.delete()
            except LowStockAlert.DoesNotExist:
                # No alert exists, nothing to do
                pass
    
    @staticmethod
    def get_active_alerts() -> QuerySet:
        """
        Retrieve all active low-stock alerts for dashboard display.
        
        Returns:
            QuerySet of active LowStockAlert instances with related products
        """
        from .models import LowStockAlert
        
        return LowStockAlert.objects.filter(
            is_active=True
        ).select_related('product', 'product__category').order_by('created_at')
