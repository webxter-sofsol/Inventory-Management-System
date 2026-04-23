from django.urls import path
from . import views, ai_views

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
    
    # Reports URLs
    path('reports/', views.reports, name='reports'),
    path('reports/export/csv/', views.export_csv, name='export_csv'),
    path('reports/export/pdf/', views.export_pdf, name='export_pdf'),

    # AI & P&L URLs
    path('ai/', ai_views.ai_insights, name='ai_insights'),
    path('ai/data/', ai_views.ai_insights_data, name='ai_insights_data'),
    path('pnl/', ai_views.pnl_dashboard, name='pnl'),
    path('ai/chat/', ai_views.ai_chat, name='ai_chat'),
    path('ai/refresh/', ai_views.refresh_insights, name='ai_refresh'),
]
