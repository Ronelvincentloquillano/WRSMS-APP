from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class SubscriptionRequiredMixin(AccessMixin):
    """
    Mixin to ensure the user's station has an active subscription.
    Redirects to the subscription expired page if not valid.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        try:
            station = request.user.profile.station
            if not station:
                # Should ideally not happen for a fully set up user
                return redirect('account:login')
            
            # Check for subscription
            if hasattr(station, 'subscription'):
                subscription = station.subscription
                if not subscription.is_valid:
                    # Allow access if we are already on the expired or payment pages to avoid loops
                    # This check is technically redundant if we don't apply the mixin to those views,
                    # but good for safety if we apply it globally later.
                    current_url_name = request.resolver_match.url_name
                    if current_url_name not in ['subscription_expired', 'initiate_payment', 'payment_callback']:
                        messages.warning(request, "Your subscription has expired. Please renew to continue.")
                        return redirect('wrsm_app:subscription_expired')
            else:
                # No subscription found - arguably this is also an expired/invalid state
                # Or we could create a default trial here if missing?
                # For now, treat as expired.
                messages.warning(request, "No subscription found.")
                return redirect('wrsm_app:subscription_expired')

        except Exception as e:
            # Handle cases where profile doesn't exist, etc.
            print(f"Subscription check error: {e}")
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)
