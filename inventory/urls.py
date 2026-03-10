from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Product management URLs
    path('products/', views.ProductListView.as_view(), name='product_list_view'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/bulk-update/', views.bulk_update_view, name='bulk_update'),
    path('products/bulk-update/submit/', views.bulk_update_submit, name='bulk_update_submit'),
    
    # Category management URLs
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Transaction URLs
    path('transactions/', views.TransactionHistoryView.as_view(), name='transaction_history'),
    path('transactions/create/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/validate-stock/', views.validate_stock, name='validate_stock'),
    
    # Other URLs
    path('reports/', views.reports, name='reports'),
]
