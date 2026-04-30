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
    """Dashboard view with real metrics"""
    from django.db.models import Sum, Count, F
    from .models import LowStockAlert

    user = request.user

    total_products = Product.objects.filter(user=user).count()
    total_value = Product.objects.filter(user=user).aggregate(
        val=Sum(F('quantity') * F('price'))
    )['val'] or 0

    out_of_stock = Product.objects.filter(user=user, quantity=0).count()
    low_stock_alerts = LowStockAlert.objects.filter(
        is_active=True, product__user=user
    ).select_related('product', 'product__category').order_by('created_at')
    low_stock_count = low_stock_alerts.count()

    recent_transactions = StockTransaction.objects.filter(
        product__user=user
    ).select_related('product', 'product__category', 'user').order_by('-timestamp')[:10]

    # Category breakdown
    categories = Category.objects.filter(user=user).annotate(
        product_count=Count('products'),
        total_qty=Sum('products__quantity'),
    ).order_by('-product_count')

    out_of_stock_products = Product.objects.filter(
        user=user, quantity=0
    ).select_related('category')[:8]

    context = {
        'total_products': total_products,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
        'low_stock_alerts': low_stock_alerts,
        'recent_transactions': recent_transactions,
        'categories': categories,
        'out_of_stock_products': out_of_stock_products,
    }
    return render(request, 'inventory/dashboard.html', context)


class ProductListView(LoginRequiredMixin, ListView):
    """Product list view with search and filtering"""
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered product queryset"""
        search_query = self.request.GET.get('search', '').strip()
        category_filter = self.request.GET.get('category', '').strip()
        stock_status_filter = self.request.GET.get('stock_status', '').strip()
        
        product_service = ProductService()
        queryset = product_service.search_products(
            user=self.request.user,
            query=search_query if search_query else None,
            category=category_filter if category_filter else None,
            stock_status=stock_status_filter if stock_status_filter else None
        )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        """Add additional context for filters"""
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user).order_by('name')
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
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limit category choices to the current user's categories
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        """Assign the current user before saving"""
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Product "{self.object.name}" created successfully.'
            )
            return response
        except Exception as e:
            messages.error(self.request, f'Error creating product: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
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

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Product "{self.object.name}" updated successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error updating product: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Edit Product: {self.object.name}'
        context['submit_text'] = 'Update Product'
        return context


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Delete product with confirmation"""
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('product_list_view')

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product_name = product.name
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, f'Product "{product_name}" deleted successfully.')
            return response
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
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
        
        products = Product.objects.filter(id__in=product_ids, user=request.user)
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


from django.http import JsonResponse, HttpResponse
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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Only show the current user's products
        form.fields['product'].queryset = Product.objects.filter(
            user=self.request.user
        ).order_by('name')
        return form

    def form_valid(self, form):
        try:
            product = form.cleaned_data['product']
            # Ensure the product belongs to the current user
            if product.user != self.request.user:
                messages.error(self.request, 'Invalid product selection.')
                return self.form_invalid(form)

            transaction_type = form.cleaned_data['transaction_type']
            quantity = form.cleaned_data['quantity_change']
            
            transaction_service = TransactionService()
            
            if transaction_type == 'purchase':
                transaction_service.record_purchase(
                    product_id=product.id,
                    quantity=quantity,
                    user_id=self.request.user.id
                )
                messages.success(
                    self.request,
                    f'Purchase recorded: {quantity} units of {product.name} added to inventory.'
                )
            else:
                transaction_service.record_sale(
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
            messages.error(self.request, f'Error recording transaction: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
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
        product = Product.objects.get(id=product_id, user=request.user)
        quantity = int(quantity)
        
        if quantity <= 0:
            return JsonResponse({'valid': False, 'message': 'Quantity must be positive'})
        
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
        transaction_service = TransactionService()
        
        product_id = self.request.GET.get('product')
        transaction_type = self.request.GET.get('transaction_type')
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
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
        
        queryset = transaction_service.get_transaction_history(
            user=self.request.user,
            product_id=int(product_id) if product_id else None,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type if transaction_type else None
        )
        
        return queryset.select_related('product', 'product__category', 'user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(user=self.request.user).order_by('name')
        context['product_filter'] = self.request.GET.get('product', '')
        context['transaction_type_filter'] = self.request.GET.get('transaction_type', '')
        context['start_date_filter'] = self.request.GET.get('start_date', '')
        context['end_date_filter'] = self.request.GET.get('end_date', '')
        return context


@login_required
def reports(request):
    """Inventory report with category filter and preview"""
    from django.db.models import Sum, Count, F, Q
    from .models import LowStockAlert

    user = request.user
    category_filter = request.GET.get('category', '').strip()

    products = Product.objects.filter(user=user).select_related('category').annotate(
        report_total_value=F('quantity') * F('price')
    )
    if category_filter:
        products = products.filter(category__name=category_filter)
    products = products.order_by('category__name', 'name')

    summary = products.aggregate(
        total_products=Count('id'),
        total_units=Sum('quantity'),
        total_value=Sum(F('quantity') * F('price')),
    )

    low_stock_count = products.filter(quantity__lt=F('alert_threshold')).count()
    out_of_stock_count = products.filter(quantity=0).count()

    categories = Category.objects.filter(user=user).order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'category_filter': category_filter,
        'summary': summary,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'inventory/reports.html', context)


@login_required
def export_csv(request):
    """Export inventory report as CSV"""
    import csv
    from django.db.models import F
    from django.utils import timezone

    category_filter = request.GET.get('category', '').strip()

    products = Product.objects.filter(user=request.user).select_related('category').order_by('category__name', 'name')
    if category_filter:
        products = products.filter(category__name=category_filter)

    filename = f"inventory_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Product Name', 'Category', 'Quantity', 'Unit Price ($)',
                     'Total Value ($)', 'Alert Threshold', 'Status'])

    for p in products:
        total_val = p.quantity * p.price
        writer.writerow([
            p.name,
            p.category.name,
            p.quantity,
            f'{p.price:.2f}',
            f'{total_val:.2f}',
            p.alert_threshold,
            p.stock_status,
        ])

    return response


@login_required
def export_pdf(request):
    """Export inventory report as PDF using ReportLab"""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from django.db.models import F
    from django.utils import timezone
    import io

    category_filter = request.GET.get('category', '').strip()

    products = Product.objects.filter(user=request.user).select_related('category').order_by('category__name', 'name')
    if category_filter:
        products = products.filter(category__name=category_filter)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', fontSize=16, fontName='Helvetica-Bold',
                                 spaceAfter=4, textColor=colors.HexColor('#111827'))
    sub_style = ParagraphStyle('sub', fontSize=9, fontName='Helvetica',
                               textColor=colors.HexColor('#6b7280'), spaceAfter=16)
    header_style = ParagraphStyle('header', fontSize=8, fontName='Helvetica-Bold',
                                  textColor=colors.white, alignment=TA_CENTER)

    elements = []

    # Title
    title_text = 'Inventory Report'
    if category_filter:
        title_text += f' — {category_filter}'
    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(
        f'Generated on {timezone.now().strftime("%B %d, %Y at %H:%M")}',
        sub_style
    ))

    # Table data
    col_headers = ['Product Name', 'Category', 'Qty', 'Unit Price', 'Total Value', 'Threshold', 'Status']
    data = [col_headers]

    status_colors = {
        'in-stock': colors.HexColor('#15803d'),
        'low-stock': colors.HexColor('#b45309'),
        'out-of-stock': colors.HexColor('#dc2626'),
    }

    for p in products:
        total_val = p.quantity * p.price
        data.append([
            p.name,
            p.category.name,
            str(p.quantity),
            f'${p.price:.2f}',
            f'${total_val:.2f}',
            str(p.alert_threshold),
            p.stock_status.replace('-', ' ').title(),
        ])

    col_widths = [6 * cm, 3.5 * cm, 2 * cm, 2.8 * cm, 3 * cm, 2.5 * cm, 3 * cm]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 8),
        ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        # Body rows
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('ALIGN',      (2, 1), (5, -1), 'CENTER'),
        ('ALIGN',      (3, 1), (4, -1), 'RIGHT'),
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        # Grid
        ('GRID',       (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
        ('LINEBELOW',  (0, 0), (-1, 0), 1, colors.HexColor('#1648c0')),
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"inventory_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response



class CategoryListView(LoginRequiredMixin, ListView):
    """Category list view"""
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        from django.db.models import Count, Sum, F
        return Category.objects.filter(user=self.request.user).annotate(
            product_count=Count('products'),
            total_qty=Sum('products__quantity'),
            total_value=Sum(F('products__quantity') * F('products__price')),
        ).order_by('name')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    """Create new category"""
    model = Category
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('category_list')
    fields = ['name', 'description']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter category name'})
        form.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter description (optional)', 'rows': 3})
        return form
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Category "{self.object.name}" created successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error creating category: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
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

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter category name'})
        form.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter description (optional)', 'rows': 3})
        return form
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Category "{self.object.name}" updated successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Error updating category: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Edit Category: {self.object.name}'
        context['submit_text'] = 'Update Category'
        return context


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete category with confirmation"""
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        category_name = category.name
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, f'Category "{category_name}" deleted successfully.')
            return response
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}. It may have associated products.')
            return redirect('category_list')
