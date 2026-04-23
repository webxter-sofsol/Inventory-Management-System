"""
AI service — wraps OpenAI to provide inventory insights, P&L analysis,
and actionable recommendations based on real inventory data.
"""
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_inventory_snapshot() -> dict:
    """Collect a compact snapshot of current inventory state for the AI prompt."""
    from django.db.models import Sum, Count, F, Q
    from .models import Product, StockTransaction, LowStockAlert, Category

    # Products
    products = list(
        Product.objects.select_related('category').values(
            'id', 'name', 'quantity', 'price', 'alert_threshold',
            'category__name', 'created_at',
        )
    )
    for p in products:
        p['total_value'] = float(Decimal(str(p['quantity'])) * Decimal(str(p['price'])))
        p['price'] = float(p['price'])
        p['created_at'] = p['created_at'].isoformat() if p['created_at'] else None

    # Transaction summary (last 90 days)
    since = timezone.now() - timezone.timedelta(days=90)
    tx_summary = (
        StockTransaction.objects
        .filter(timestamp__gte=since)
        .values('product__name', 'transaction_type')
        .annotate(total_qty=Sum('quantity_change'), count=Count('id'))
        .order_by('product__name')
    )

    # Revenue & cost estimates
    sales = (
        StockTransaction.objects
        .filter(transaction_type='sale', timestamp__gte=since)
        .select_related('product')
    )
    total_revenue = sum(
        abs(tx.quantity_change) * tx.product.price for tx in sales
    )

    purchases = (
        StockTransaction.objects
        .filter(transaction_type='purchase', timestamp__gte=since)
        .select_related('product')
    )
    total_cost = sum(
        tx.quantity_change * tx.product.price for tx in purchases
    )

    low_stock = list(
        LowStockAlert.objects.filter(is_active=True)
        .select_related('product', 'product__category')
        .values('product__name', 'product__quantity', 'product__alert_threshold', 'product__price')
    )

    categories = list(
        Category.objects.annotate(
            product_count=Count('products'),
            total_qty=Sum('products__quantity'),
            total_value=Sum(F('products__quantity') * F('products__price')),
        ).values('name', 'product_count', 'total_qty', 'total_value')
    )
    for c in categories:
        c['total_value'] = float(c['total_value'] or 0)

    return {
        'snapshot_date': timezone.now().isoformat(),
        'products': products,
        'transaction_summary_90d': list(tx_summary),
        'financials_90d': {
            'total_revenue': float(total_revenue),
            'total_cost': float(total_cost),
            'gross_profit': float(total_revenue - total_cost),
        },
        'low_stock_alerts': low_stock,
        'categories': categories,
        'totals': {
            'total_products': len(products),
            'total_inventory_value': sum(p['total_value'] for p in products),
            'out_of_stock': sum(1 for p in products if p['quantity'] == 0),
            'low_stock': len(low_stock),
        },
    }


def _log_interaction(service_name: str, request_data: dict, response_data: dict):
    """Persist AI interaction to the database."""
    try:
        from .models import AIInteractionLog
        AIInteractionLog.objects.create(
            service_name=service_name,
            request_data=request_data,
            response_data=response_data,
        )
    except Exception as e:
        logger.warning(f"Failed to log AI interaction: {e}")


def get_ai_insights() -> dict:
    """
    Ask OpenAI for a structured analysis of the current inventory.
    Returns a dict with keys: summary, recommendations, alerts, predictions.
    """
    if not settings.OPENAI_API_KEY:
        return _fallback_response("OpenAI API key not configured.")

    snapshot = _build_inventory_snapshot()

    system_prompt = """You are an expert inventory management consultant and financial analyst.
You analyse inventory data and provide concise, actionable business insights.
Always respond with valid JSON matching this exact schema:
{
  "summary": "2-3 sentence executive summary of inventory health",
  "health_score": <integer 0-100>,
  "recommendations": [
    {"priority": "high|medium|low", "title": "...", "detail": "...", "action": "..."},
    ...
  ],
  "alerts": [
    {"type": "warning|danger|info", "title": "...", "message": "..."},
    ...
  ],
  "predictions": {
    "next_30_days": {
      "expected_revenue": <number>,
      "expected_cost": <number>,
      "expected_profit": <number>,
      "confidence": "low|medium|high",
      "reasoning": "..."
    },
    "risks": ["...", "..."],
    "opportunities": ["...", "..."]
  }
}
Keep each recommendation detail under 120 characters. Be specific and data-driven."""

    user_prompt = f"""Analyse this inventory snapshot and provide insights:

{json.dumps(snapshot, indent=2, default=str)}

Focus on:
1. Profitability trends from the 90-day transaction data
2. Stock health (low stock, dead stock, overstocked items)
3. Revenue optimisation opportunities
4. Risk factors that could cause losses
5. Specific reorder recommendations with quantities"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        _log_interaction(
            service_name="inventory_insights",
            request_data={"snapshot_totals": snapshot['totals'], "financials": snapshot['financials_90d']},
            response_data=result,
        )
        return result

    except Exception as e:
        logger.error(f"OpenAI insights error: {e}")
        return _fallback_response(str(e))


def get_pnl_analysis() -> dict:
    """
    Returns computed P&L data (no AI needed) plus AI commentary.
    """
    from django.db.models import Sum, F
    from .models import StockTransaction
    import calendar

    now = timezone.now()

    # Build monthly P&L for last 6 months
    monthly = []
    for i in range(5, -1, -1):
        month_date = now - timezone.timedelta(days=30 * i)
        year, month = month_date.year, month_date.month
        _, last_day = calendar.monthrange(year, month)

        start = timezone.datetime(year, month, 1, tzinfo=timezone.utc)
        end = timezone.datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        sales_qs = StockTransaction.objects.filter(
            transaction_type='sale', timestamp__range=(start, end)
        ).select_related('product')
        purchases_qs = StockTransaction.objects.filter(
            transaction_type='purchase', timestamp__range=(start, end)
        ).select_related('product')

        revenue = sum(abs(tx.quantity_change) * tx.product.price for tx in sales_qs)
        cost = sum(tx.quantity_change * tx.product.price for tx in purchases_qs)
        profit = revenue - cost

        monthly.append({
            'label': month_date.strftime('%b %Y'),
            'revenue': float(revenue),
            'cost': float(cost),
            'profit': float(profit),
            'transactions': sales_qs.count() + purchases_qs.count(),
        })

    # Top products by revenue (90 days)
    since = now - timezone.timedelta(days=90)
    sales = (
        StockTransaction.objects
        .filter(transaction_type='sale', timestamp__gte=since)
        .select_related('product', 'product__category')
    )
    product_revenue: dict = {}
    for tx in sales:
        key = tx.product.name
        if key not in product_revenue:
            product_revenue[key] = {
                'name': key,
                'category': tx.product.category.name,
                'units_sold': 0,
                'revenue': Decimal('0'),
            }
        product_revenue[key]['units_sold'] += abs(tx.quantity_change)
        product_revenue[key]['revenue'] += abs(tx.quantity_change) * tx.product.price

    top_products = sorted(
        [{'name': v['name'], 'category': v['category'],
          'units_sold': v['units_sold'], 'revenue': float(v['revenue'])}
         for v in product_revenue.values()],
        key=lambda x: x['revenue'], reverse=True
    )[:10]

    totals = {
        'total_revenue': sum(m['revenue'] for m in monthly),
        'total_cost': sum(m['cost'] for m in monthly),
        'total_profit': sum(m['profit'] for m in monthly),
    }

    return {
        'monthly': monthly,
        'top_products': top_products,
        'totals': totals,
    }


def ask_ai_question(question: str) -> str:
    """Free-form question about the inventory — returns a plain text answer."""
    if not settings.OPENAI_API_KEY:
        return "AI is not configured. Please add your OpenAI API key to the .env file."

    snapshot = _build_inventory_snapshot()

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an inventory management assistant. "
                        "Answer questions concisely based on the provided inventory data. "
                        "Be specific, use numbers from the data, and give actionable advice. "
                        "Keep answers under 200 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Inventory data:\n{json.dumps(snapshot, indent=2, default=str)}\n\nQuestion: {question}",
                },
            ],
            temperature=0.4,
            max_tokens=400,
        )
        answer = response.choices[0].message.content

        _log_interaction(
            service_name="ai_chat",
            request_data={"question": question},
            response_data={"answer": answer},
        )
        return answer

    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        return f"Sorry, I couldn't process that question right now. ({e})"


def _fallback_response(reason: str) -> dict:
    return {
        "summary": f"AI insights unavailable: {reason}",
        "health_score": 0,
        "recommendations": [],
        "alerts": [{"type": "warning", "title": "AI Unavailable", "message": reason}],
        "predictions": {
            "next_30_days": {
                "expected_revenue": 0, "expected_cost": 0, "expected_profit": 0,
                "confidence": "low", "reasoning": reason,
            },
            "risks": [], "opportunities": [],
        },
    }
