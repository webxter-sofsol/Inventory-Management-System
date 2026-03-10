from django.contrib import admin
from .models import Category, Product, StockTransaction, LowStockAlert, AIInteractionLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'price', 'stock_status', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity_change', 'user', 'timestamp']
    list_filter = ['transaction_type', 'timestamp']
    search_fields = ['product__name']
    readonly_fields = ['timestamp']


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['created_at']


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'timestamp']
    list_filter = ['service_name', 'timestamp']
    readonly_fields = ['timestamp']
