from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def subscription_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                # Ensure profile exists
                if not hasattr(request.user, 'profile'):
                    return function(request, *args, **kwargs)

                station = request.user.profile.station
                if not station:
                    return function(request, *args, **kwargs)

                if hasattr(station, 'subscription'):
                    if not station.subscription.is_valid:
                        messages.warning(request, "Your subscription has expired.")
                        return redirect('wrsm_app:subscription_expired')
                else:
                    # No subscription found - assume expired/invalid
                    messages.warning(request, "Subscription required.")
                    return redirect('wrsm_app:subscription_expired')
            except Exception as e:
                # Log error if needed, but don't block access if check fails unexpectedly?
                # Or block to be safe. Let's print for now.
                print(f"Subscription check error: {e}")
                pass 
        return function(request, *args, **kwargs)
    return wrap
