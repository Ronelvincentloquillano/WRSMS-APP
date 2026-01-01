from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Sales, Notification, Profile
from account.models import StationSubscription

def check_transaction_limit(station, request=None):
    try:
        if not hasattr(station, 'subscription'):
            return

        subscription = station.subscription
        if not subscription or not subscription.is_active:
            return

        plan = subscription.plan
        if not plan or plan.transaction_limit is None:
            return

        limit = plan.transaction_limit
        
        # Count sales for current month
        # Use local time for correct month boundary
        now = timezone.now()
        if timezone.is_aware(now):
            now = timezone.localtime(now)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        sales_count = Sales.objects.filter(
            station=station,
            created_date__gte=start_of_month
        ).count()

        threshold = int(limit * 0.8)
        
        notification_type = None
        message = ""
        subject = ""

        if sales_count >= limit:
            notification_type = 'LIMIT_REACHED'
            message = f"Urgent: You have reached your transaction limit of {limit} for this month. Please upgrade your plan to continue adding sales."
            subject = "Transaction Limit Reached"
        elif sales_count >= threshold:
            notification_type = 'LIMIT_WARNING'
            message = f"Warning: You have used {sales_count} of your {limit} transaction limit (80%)."
            subject = "Transaction Limit Warning"
        
        if notification_type:
            # Check if we already notified for this type this month
            already_notified = Notification.objects.filter(
                station=station,
                type=notification_type,
                created_at__gte=start_of_month
            ).exists()

            if not already_notified:
                # Create In-App Notification
                Notification.objects.create(
                    station=station,
                    user=request.user if request else None,
                    type=notification_type,
                    message=message
                )

                # Send Email to all station owners
                # Find profiles linked to station who are likely owners (or just current user if owner)
                # Ideally, we email the user who initiated the action + other admins.
                recipient_list = []
                if request and request.user.email:
                    recipient_list.append(request.user.email)
                
                # Deduplicate
                recipient_list = list(set(recipient_list))
                
                if recipient_list:
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            recipient_list,
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"Failed to send email: {e}")

    except Exception as e:
        print(f"Error checking limit: {e}")


def is_transaction_limit_reached(station):
    """
    Returns True if the station has reached its transaction limit for the current month.
    """
    try:
        if not hasattr(station, 'subscription'):
            return False

        subscription = station.subscription
        if not subscription or not subscription.is_active:
            # If no active subscription, maybe block? Or allow? 
            # Assuming active subscription is required for limit check.
            # If is_active=False, usually means expired, so maybe block?
            # But the requirement is about "transaction limit".
            # Let's assume unlimited if no plan defined, or 0? 
            # Existing code: if not active return (no check).
            return False

        plan = subscription.plan
        if not plan or plan.transaction_limit is None:
            return False

        limit = plan.transaction_limit
        
        now = timezone.now()
        if timezone.is_aware(now):
            now = timezone.localtime(now)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        sales_count = Sales.objects.filter(
            station=station,
            created_date__gte=start_of_month
        ).count()

        return sales_count >= limit

    except Exception as e:
        print(f"Error checking limit reached: {e}")
        return False
