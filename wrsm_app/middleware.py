from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # PWA install / offline shell must never hit subscription redirects
        if request.path in ('/manifest.json', '/serviceworker.js', '/offline/'):
            return self.get_response(request)

        if request.user.is_authenticated:
            # List of namespaces/view_names allowed even if expired
            ALLOWED_VIEWS = [
                'account:logout',
                'account:password_change',
                'account:password_change_done',
                'wrsm_app:subscription_expired',
                'wrsm_app:initiate_payment',
                'wrsm_app:payment_callback',
                'wrsm_app:submit-manual-payment',
                'wrsm_app:subscription-payment-requests',
                'wrsm_app:approve-subscription-payment',
                'wrsm_app:reject-subscription-payment',
                'wrsm_app:offline_master_data',
                'wrsm_app:profile',
                'wrsm_app:register-new-station',
                'wrsm_app:station-list',
                'wrsm_app:switch-station',
                'wrsm_app:setup-wizard',
                'wrsm_app:admin-settings-portal',
                'admin:index',
                'admin:login',
                'account:login', # Just in case
            ]

            # Determine current view name
            if not getattr(request, 'resolver_match', None):
                try:
                    request.resolver_match = resolve(request.path)
                except:
                    pass

            current_view_name = None
            if request.resolver_match:
                current_view_name = request.resolver_match.view_name
            
            # Prevent loop: If we are already at the subscription expired page, let it pass
            # We check both view name and path to be safe
            expired_url = reverse('wrsm_app:subscription_expired')
            initiate_payment_url = reverse('wrsm_app:initiate_payment')
            payment_callback_url = reverse('wrsm_app:payment_callback')
            submit_manual_payment_url = reverse('wrsm_app:submit-manual-payment')

            # Allow critical subscription urls by path comparison as well
            if request.path in [expired_url, initiate_payment_url, payment_callback_url, submit_manual_payment_url]:
                return self.get_response(request)

            if current_view_name in [
                'wrsm_app:subscription_expired',
                'wrsm_app:initiate_payment',
                'wrsm_app:payment_callback',
                'wrsm_app:submit-manual-payment',
                'wrsm_app:subscription-payment-requests',
                'wrsm_app:approve-subscription-payment',
                'wrsm_app:reject-subscription-payment',
            ]:
                return self.get_response(request)

            # Check for static/media assets (usually handled upstream, but good practice)
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                return self.get_response(request)
            
            # Superusers bypass
            if request.user.is_superuser:
                 return self.get_response(request)

            # Check Subscription Status
            is_valid = True
            try:
                # Safely access profile and station
                # We use getattr with default None to avoid AttributeError if profile missing
                # But request.user.profile raises ObjectDoesNotExist if missing on OneToOne
                try:
                    profile = request.user.profile
                except ObjectDoesNotExist:
                    profile = None
                
                if profile and profile.station:
                    station = profile.station
                    
                    # Check subscription
                    # StationSubscription reverse relation
                    try:
                        subscription = station.subscription
                        if not subscription.is_valid:
                            is_valid = False
                    except ObjectDoesNotExist:
                        # No subscription = invalid
                        is_valid = False
                else:
                    # No profile or station found = invalid
                    is_valid = False
            except Exception as e:
                # Log unexpected errors to console
                print(f"SubscriptionMiddleware Check Error: {e}")
                # Fail CLOSED: If we can't verify, we block.
                is_valid = False

            if not is_valid:
                # Check if current view is allowed
                is_allowed = False
                
                # Exact match check
                if current_view_name in ALLOWED_VIEWS:
                    is_allowed = True
                
                # Admin check (allow all admin sub-urls if user has access)
                if current_view_name and current_view_name.startswith('admin:'):
                    is_allowed = True

                if not is_allowed:
                    messages.warning(request, "Subscription expired. Access restricted.")
                    return redirect('wrsm_app:subscription_expired')

        return self.get_response(request)
