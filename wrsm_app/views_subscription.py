from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from account.models import StationSubscription, SubscriptionPlan
from .paymongo_config import create_gcash_source, retrieve_source, create_payment

@login_required
def subscription_expired(request):
    plans = SubscriptionPlan.objects.all()
    # If no plans exist, maybe create default or handle gracefully
    context = {
        'plans': plans
    }
    return render(request, 'wrsm_app/subscription_expired.html', context)

@login_required
def initiate_payment(request):
    if request.method == 'POST':
        try:
            plan_id = request.POST.get('plan_id')
            if not plan_id:
                messages.error(request, "Please select a subscription plan.")
                return redirect('wrsm_app:subscription_expired')

            plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
            amount = float(plan.price)
            
            # Success and Fail URLs
            success_url = request.build_absolute_uri(reverse('wrsm_app:payment_callback'))
            failed_url = request.build_absolute_uri(reverse('wrsm_app:subscription_expired'))
            
            # Call PayMongo
            source = create_gcash_source(amount, success_url, failed_url)
            
            if source and 'data' in source:
                source_data = source['data']
                checkout_url = source_data['attributes']['redirect']['checkout_url']
                source_id = source_data['id']
                
                # Save source_id to session to verify callback
                request.session['paymongo_source_id'] = source_id
                request.session['pending_plan_id'] = plan.id
                
                return redirect(checkout_url)
            else:
                messages.error(request, "Failed to initiate payment with PayMongo. Please try again.")
                return redirect('wrsm_app:subscription_expired')
        except Exception as e:
            print(f"Payment Init Error: {e}")
            messages.error(request, "An error occurred while initiating payment.")
            return redirect('wrsm_app:subscription_expired')
    
    return redirect('wrsm_app:subscription_expired')

@login_required
def payment_callback(request):
    source_id = request.session.get('paymongo_source_id')
    if not source_id:
        messages.error(request, "No pending payment found.")
        return redirect('wrsm_app:dashboard')
        
    # Verify status
    source_response = retrieve_source(source_id)
    if source_response and 'data' in source_response:
        attributes = source_response['data']['attributes']
        status = attributes['status']
        
        if status == 'chargeable':
            amount = attributes['amount'] / 100.0 # Convert back to main unit
            
            # Finalize Payment
            payment_response = create_payment(source_id, amount, "Subscription Renewal")
            
            if payment_response and 'data' in payment_response:
                # Update Subscription
                station = request.user.profile.station
                subscription, created = StationSubscription.objects.get_or_create(station=station)
                
                # Extend for 30 days
                # If expired, start from today. If active, add to end_date?
                # For simplicity, let's reset to 30 days from today if expired.
                
                new_end_date = timezone.now().date() + timedelta(days=30)
                if subscription.end_date and subscription.end_date > timezone.now().date():
                     new_end_date = subscription.end_date + timedelta(days=30)
                
                subscription.end_date = new_end_date
                subscription.is_active = True
                subscription.is_trial = False # No longer trial
                
                plan_id = request.session.get('pending_plan_id')
                if plan_id:
                    subscription.plan_id = plan_id
                
                subscription.save()
                
                # Clear session
                del request.session['paymongo_source_id']
                if 'pending_plan_id' in request.session:
                    del request.session['pending_plan_id']
                
                messages.success(request, "Payment successful! Subscription renewed.")
                return redirect('wrsm_app:dashboard')
            else:
                messages.error(request, "Payment processing failed.")
        else:
             messages.error(request, f"Payment status: {status}")
    else:
        messages.error(request, "Could not verify payment status.")
        
    return redirect('wrsm_app:subscription_expired')