from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal


class Category(models.Model):
    """Product category"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Inventory product"""
    name = models.CharField(max_length=200, db_index=True)
    quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Current stock quantity"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    alert_threshold = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Minimum quantity before alert"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['quantity']),
        ]
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total value of product stock"""
        return self.quantity * self.price
    
    @property
    def is_low_stock(self) -> bool:
        """Check if product is below alert threshold"""
        return self.quantity < self.alert_threshold
    
    @property
    def stock_status(self) -> str:
        """Return stock status: in-stock, low-stock, out-of-stock"""
        if self.quantity == 0:
            return 'out-of-stock'
        elif self.is_low_stock:
            return 'low-stock'
        return 'in-stock'
    
    def __str__(self):
        return self.name


class StockTransaction(models.Model):
    """Record of inventory changes"""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
    ]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        db_index=True
    )
    quantity_change = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['product', '-timestamp']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} ({self.quantity_change})"



class LowStockAlert(models.Model):
    """Alert for products below threshold"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='alert'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = 'low_stock_alerts'
        indexes = [
            models.Index(fields=['is_active', 'created_at']),
        ]
    
    def __str__(self):
        return f"Alert: {self.product.name} (Active: {self.is_active})"


class AIInteractionLog(models.Model):
    """Log of AI service interactions"""
    service_name = models.CharField(max_length=100)
    request_data = models.JSONField()
    response_data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'ai_interaction_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.service_name} - {self.timestamp}"
