from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from wrsm_app.models import Station, Profile
from account.models import StationSubscription, SubscriptionPlan

# Ensure our middleware is in the list for the test
@override_settings(MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'wrsm_app.middleware.SubscriptionMiddleware', 
])
class SubscriptionAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.station = Station.objects.create(name='Test Station', station_code='TEST01')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        # Create a plan
        self.plan = SubscriptionPlan.objects.create(name='Test Plan', price=100.00)
        
        # Create an EXPIRED subscription
        # Ended yesterday
        yesterday = timezone.now().date() - timedelta(days=1)
        self.subscription = StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=yesterday - timedelta(days=30),
            end_date=yesterday,
            is_active=True
        )
        
        self.client.login(username='testuser', password='password')

    def test_add_customer_access_expired(self):
        """
        Test that accessing add-customer is BLOCKED when subscription is expired.
        """
        url = reverse('wrsm_app:add-customer')
        response = self.client.get(url)
        
        # We expect 302 because the bug is fixed (it blocks access)
        self.assertRedirects(response, reverse('wrsm_app:subscription_expired'))

    def test_customers_list_access_expired(self):
        url = reverse('wrsm_app:customers')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('wrsm_app:subscription_expired'))
