"""
AI-powered views: insights dashboard, P&L page, and chat endpoint.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse


@login_required
def ai_insights(request):
    """Render the shell instantly — insights are fetched async via /ai/data/."""
    return render(request, 'inventory/ai_insights.html')


@login_required
def ai_insights_data(request):
    """JSON endpoint — called by the page after load. Does the OpenAI call."""
    from .ai_service import get_ai_insights
    try:
        insights = get_ai_insights(user=request.user)
        response = JsonResponse({'ok': True, 'insights': insights})
    except Exception as e:
        response = JsonResponse({'ok': False, 'error': str(e)}, status=500)

    # Prevent browser and proxy caching — insights must always reflect live data
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def pnl_dashboard(request):
    """Profit & Loss dashboard — pure Python, no AI call, loads fast."""
    from .ai_service import get_pnl_analysis
    pnl = get_pnl_analysis(user=request.user)
    response = render(request, 'inventory/pnl.html', {'pnl': pnl})
    # Prevent browser caching so data always reflects the latest transactions
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def ai_chat(request):
    """AJAX endpoint — answer a free-form question about inventory."""
    question = request.GET.get('q', '').strip()
    if not question:
        return JsonResponse({'answer': 'Please ask a question.'})
    from .ai_service import ask_ai_question
    answer = ask_ai_question(question, user=request.user)
    response = JsonResponse({'answer': answer})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response


@login_required
def refresh_insights(request):
    """Alias for ai_insights_data — used by the refresh button."""
    return ai_insights_data(request)
