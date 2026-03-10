from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product, Category
from .forms import ProductForm
from .services import ProductService


@login_required
def dashboard(request):
    """Dashboard view - requires authentication"""
    return render(request, 'inventory/dashboard.html')


class ProductListView(LoginRequiredMixin, ListView):
    """Product list view with search and filtering"""
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered product queryset"""
        queryset = Product.objects.select_related('category').all()
        
        # Get filter parameters
        search_query = self.request.GET.get('search', '').strip()
        category_filter = self.request.GET.get('category', '').strip()
        stock_status_filter = self.request.GET.get('stock_status', '').strip()
        
        # Use ProductService for filtering
        product_service = ProductService()
        queryset = product_service.search_products(
            query=search_query if search_query else None,
            category=category_filter if category_filter else None,
            stock_status=stock_status_filter if stock_status_filter else None
        )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context for filters"""
        context = super().get_context_data(**kwargs)
        
        # Add categories for filter dropdown
        context['categories'] = Category.objects.all().order_by('name')
        
        # Preserve filter values in context
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['stock_status_filter'] = self.request.GET.get('stock_status', '')
        
        return context


def product_list(request):
    """Product list view - redirect to class-based view"""
    from django.urls import reverse
    return redirect('product_list_view')


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Create new product"""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list_view')
    
    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Product "{self.object.name}" created successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error creating product: {str(e)}'
            )
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Add New Product'
        context['submit_text'] = 'Create Product'
        return context


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing product"""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('product_list_view')
    
    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Product "{self.object.name}" updated successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating product: {str(e)}'
            )
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Edit Product: {self.object.name}'
        context['submit_text'] = 'Update Product'
        return context


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Delete product with confirmation"""
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('product_list_view')
    
    def delete(self, request, *args, **kwargs):
        """Handle product deletion"""
        product = self.get_object()
        product_name = product.name
        
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(
                request,
                f'Product "{product_name}" deleted successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                request,
                f'Error deleting product: {str(e)}'
            )
            return redirect('product_list_view')


@login_required
def bulk_update_view(request):
    """Handle bulk updates for quantities and prices"""
    if request.method == 'POST':
        operation = request.POST.get('operation')
        product_ids = request.POST.getlist('product_ids')
        
        if not product_ids:
            messages.error(request, 'No products selected.')
            return redirect('product_list_view')
        
        # Render inline editing form
        products = Product.objects.filter(id__in=product_ids)
        return render(request, 'inventory/bulk_update_form.html', {
            'products': products,
            'operation': operation
        })
    
    return redirect('product_list_view')


@login_required
def bulk_update_submit(request):
    """Process bulk update submission"""
    if request.method == 'POST':
        operation = request.POST.get('operation')
        product_service = ProductService()
        
        try:
            updates = []
            for key, value in request.POST.items():
                if key.startswith('product_'):
                    product_id = int(key.split('_')[1])
                    
                    if operation == 'quantity':
                        updates.append({
                            'id': product_id,
                            'quantity': int(value)
                        })
                    elif operation == 'price':
                        from decimal import Decimal
                        updates.append({
                            'id': product_id,
                            'price': Decimal(value)
                        })
            
            # Perform bulk update
            if operation == 'quantity':
                updated = product_service.bulk_update_quantities(updates)
                messages.success(
                    request,
                    f'Successfully updated quantities for {len(updated)} products.'
                )
            elif operation == 'price':
                updated = product_service.bulk_update_prices(updates)
                messages.success(
                    request,
                    f'Successfully updated prices for {len(updated)} products.'
                )
            
        except Exception as e:
            messages.error(request, f'Error during bulk update: {str(e)}')
    
    return redirect('product_list_view')


from django.http import JsonResponse
from .services import TransactionService
from .forms import TransactionForm
from .models import StockTransaction
from datetime import datetime


class TransactionCreateView(LoginRequiredMixin, CreateView):
    """Create new stock transaction (purchase or sale)"""
    model = StockTransaction
    form_class = TransactionForm
    template_name = 'inventory/transaction_form.html'
    success_url = reverse_lazy('transaction_history')
    
    def form_valid(self, form):
        """Handle successful form submission using TransactionService"""
        try:
            product = form.cleaned_data['product']
            transaction_type = form.cleaned_data['transaction_type']
            quantity = form.cleaned_data['quantity_change']
            
            transaction_service = TransactionService()
            
            if transaction_type == 'purchase':
                transaction = transaction_service.record_purchase(
                    product_id=product.id,
                    quantity=quantity,
                    user_id=self.request.user.id
                )
                messages.success(
                    self.request,
                    f'Purchase recorded: {quantity} units of {product.name} added to inventory.'
                )
            else:  # sale
                transaction = transaction_service.record_sale(
                    product_id=product.id,
                    quantity=quantity,
                    user_id=self.request.user.id
                )
                messages.success(
                    self.request,
                    f'Sale recorded: {quantity} units of {product.name} sold.'
                )
            
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error recording transaction: {str(e)}'
            )
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Record Transaction'
        context['submit_text'] = 'Record Transaction'
        return context


@login_required
def validate_stock(request):
    """HTMX endpoint for real-time stock validation"""
    product_id = request.GET.get('product_id')
    quantity = request.GET.get('quantity')
    transaction_type = request.GET.get('transaction_type')
    
    if not all([product_id, quantity, transaction_type]):
        return JsonResponse({'valid': False, 'message': 'Missing parameters'})
    
    try:
        product = Product.objects.get(id=product_id)
        quantity = int(quantity)
        
        if quantity <= 0:
            return JsonResponse({
                'valid': False,
                'message': 'Quantity must be positive'
            })
        
        if transaction_type == 'sale':
            if product.quantity < quantity:
                return JsonResponse({
                    'valid': False,
                    'message': f'Insufficient inventory. Only {product.quantity} units available.'
                })
        
        return JsonResponse({
            'valid': True,
            'message': f'Valid. Current stock: {product.quantity} units',
            'current_stock': product.quantity
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'valid': False, 'message': 'Product not found'})
    except ValueError:
        return JsonResponse({'valid': False, 'message': 'Invalid quantity'})
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})


class TransactionHistoryView(LoginRequiredMixin, ListView):
    """Transaction history view with filtering"""
    model = StockTransaction
    template_name = 'inventory/transaction_history.html'
    context_object_name = 'transactions'
    paginate_by = 50
    
    def get_queryset(self):
        """Get filtered transaction queryset"""
        transaction_service = TransactionService()
        
        # Get filter parameters
        product_id = self.request.GET.get('product')
        transaction_type = self.request.GET.get('transaction_type')
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Use TransactionService for filtering
        queryset = transaction_service.get_transaction_history(
            product_id=int(product_id) if product_id else None,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type if transaction_type else None
        )
        
        # Prefetch related data for performance
        return queryset.select_related('product', 'product__category', 'user')
    
    def get_context_data(self, **kwargs):
        """Add additional context for filters"""
        context = super().get_context_data(**kwargs)
        
        # Add products for filter dropdown
        context['products'] = Product.objects.all().order_by('name')
        
        # Preserve filter values in context
        context['product_filter'] = self.request.GET.get('product', '')
        context['transaction_type_filter'] = self.request.GET.get('transaction_type', '')
        context['start_date_filter'] = self.request.GET.get('start_date', '')
        context['end_date_filter'] = self.request.GET.get('end_date', '')
        
        return context


def reports(request):
    """Reports view - placeholder"""
    return render(request, 'inventory/reports.html')



class CategoryListView(LoginRequiredMixin, ListView):
    """Category list view"""
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        """Get categories ordered by name"""
        return Category.objects.all().order_by('name')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    """Create new category"""
    model = Category
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category_list')
    fields = ['name', 'description']
    
    def get_form(self, form_class=None):
        """Customize form widgets"""
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter category name'})
        form.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter description (optional)', 'rows': 3})
        return form
    
    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Category "{self.object.name}" created successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error creating category: {str(e)}'
            )
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Add New Category'
        context['submit_text'] = 'Create Category'
        return context


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing category"""
    model = Category
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category_list')
    fields = ['name', 'description']
    
    def get_form(self, form_class=None):
        """Customize form widgets"""
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter category name'})
        form.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter description (optional)', 'rows': 3})
        return form
    
    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Category "{self.object.name}" updated successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating category: {str(e)}'
            )
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Edit Category: {self.object.name}'
        context['submit_text'] = 'Update Category'
        return context


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete category with confirmation"""
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')
    
    def delete(self, request, *args, **kwargs):
        """Handle category deletion"""
        category = self.get_object()
        category_name = category.name
        
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(
                request,
                f'Category "{category_name}" deleted successfully.'
            )
            return response
        except Exception as e:
            messages.error(
                request,
                f'Error deleting category: {str(e)}. It may have associated products.'
            )
            return redirect('category_list')
