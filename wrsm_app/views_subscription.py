import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from account.models import StationSubscription, SubscriptionPlan, SubscriptionPaymentRequest
from wrsm_app.models import StationSetting
from .paymongo_config import create_gcash_source, retrieve_source, create_payment

logger = logging.getLogger(__name__)


def _clear_payment_session(request):
    """Clear payment-related session keys so user can retry."""
    for key in ('paymongo_source_id', 'pending_plan_id', 'pending_billing_cycle'):
        if key in request.session:
            del request.session[key]


@login_required
def subscription_expired(request):
    plans = SubscriptionPlan.objects.all().order_by('id')
    pending_request = None
    station_settings = None
    station = None
    try:
        station = request.user.profile.station
    except ObjectDoesNotExist:
        station = None

    if station:
        pending_request = SubscriptionPaymentRequest.objects.filter(
            station=station,
            status='pending',
        ).first()
        station_settings = StationSetting.objects.filter(station=station).order_by('-pk').first()

    context = {
        'plans': plans,
        'pending_request': pending_request,
        'gcash_account_name': getattr(settings, 'GCASH_ACCOUNT_NAME', ''),
        'gcash_account_number': getattr(settings, 'GCASH_ACCOUNT_NUMBER', ''),
        'gcash_qr_url': (station_settings.gcash_qr_image.url if station_settings and station_settings.gcash_qr_image else ''),
    }
    return render(request, 'wrsm_app/subscription_expired.html', context)


@login_required
@require_POST
def submit_manual_payment(request):
    station = getattr(request.user.profile, 'station', None)
    if not station:
        messages.error(request, "No station assigned to your profile.")
        return redirect('wrsm_app:subscription_expired')

    if SubscriptionPaymentRequest.objects.filter(station=station, status='pending').exists():
        messages.warning(request, "You already have a pending payment request. Please wait for review.")
        return redirect('wrsm_app:subscription_expired')

    plan_id = request.POST.get('plan_id')
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    reference_number = (request.POST.get('reference_number') or '').strip()
    payer_name = (request.POST.get('payer_name') or '').strip()
    payer_number = (request.POST.get('payer_number') or '').strip()
    proof_image = request.FILES.get('proof_image')

    if not plan_id:
        messages.error(request, "Please select a subscription plan.")
        return redirect('wrsm_app:subscription_expired')
    if not reference_number:
        messages.error(request, "Please provide your payment reference number.")
        return redirect('wrsm_app:subscription_expired')
    if not proof_image:
        messages.error(request, "Please upload your payment proof screenshot.")
        return redirect('wrsm_app:subscription_expired')
    if billing_cycle not in ('monthly', 'annual'):
        messages.error(request, "Invalid billing cycle.")
        return redirect('wrsm_app:subscription_expired')

    plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    amount = plan.price_annual if billing_cycle == 'annual' else plan.price_monthly

    SubscriptionPaymentRequest.objects.create(
        station=station,
        plan=plan,
        billing_cycle=billing_cycle,
        amount=amount,
        reference_number=reference_number,
        payer_name=payer_name,
        payer_number=payer_number,
        proof_image=proof_image,
        created_by=request.user,
    )
    messages.success(request, "Payment proof submitted. Please wait for admin approval.")
    return redirect('wrsm_app:subscription_expired')


@login_required
def subscription_payment_requests(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('wrsm_app:dashboard')

    pending_requests = SubscriptionPaymentRequest.objects.filter(status='pending').select_related('station', 'plan', 'created_by')
    reviewed_requests = SubscriptionPaymentRequest.objects.exclude(status='pending').select_related('station', 'plan', 'reviewed_by')[:100]
    return render(request, 'wrsm_app/subscription_payment_requests.html', {
        'pending_requests': pending_requests,
        'reviewed_requests': reviewed_requests,
    })


@login_required
@require_POST
def approve_subscription_payment(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('wrsm_app:dashboard')

    payment_request = get_object_or_404(SubscriptionPaymentRequest, pk=pk)
    if payment_request.status != 'pending':
        messages.warning(request, "This request has already been reviewed.")
        return redirect('wrsm_app:subscription-payment-requests')

    subscription, _ = StationSubscription.objects.get_or_create(station=payment_request.station)
    days_to_add = 365 if payment_request.billing_cycle == 'annual' else 30
    today = timezone.now().date()
    new_end_date = today + timedelta(days=days_to_add)
    if subscription.end_date and subscription.end_date > today:
        new_end_date = subscription.end_date + timedelta(days=days_to_add)

    subscription.plan = payment_request.plan
    subscription.end_date = new_end_date
    subscription.is_active = True
    subscription.is_trial = False
    subscription.save()

    payment_request.status = 'approved'
    payment_request.reviewed_by = request.user
    payment_request.reviewed_at = timezone.now()
    payment_request.admin_note = (request.POST.get('admin_note') or '').strip()
    payment_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_note'])

    messages.success(request, "Payment request approved and subscription updated.")
    return redirect('wrsm_app:subscription-payment-requests')


@login_required
@require_POST
def reject_subscription_payment(request, pk):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access denied.")
        return redirect('wrsm_app:dashboard')

    payment_request = get_object_or_404(SubscriptionPaymentRequest, pk=pk)
    if payment_request.status != 'pending':
        messages.warning(request, "This request has already been reviewed.")
        return redirect('wrsm_app:subscription-payment-requests')

    note = (request.POST.get('admin_note') or '').strip()
    payment_request.status = 'rejected'
    payment_request.reviewed_by = request.user
    payment_request.reviewed_at = timezone.now()
    payment_request.admin_note = note
    payment_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_note'])
    messages.success(request, "Payment request rejected.")
    return redirect('wrsm_app:subscription-payment-requests')


@login_required
def initiate_payment(request):
    messages.info(
        request,
        "PayMongo payments are temporarily disabled. Please submit your payment proof via the manual GCash flow.",
    )
    return redirect('wrsm_app:subscription_expired')

@login_required
def payment_callback(request):
    _clear_payment_session(request)
    messages.info(
        request,
        "PayMongo callback is disabled temporarily. Please use manual GCash proof submission for renewal.",
    )
    return redirect('wrsm_app:subscription_expired')