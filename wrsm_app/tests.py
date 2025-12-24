from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from wrsm_app.models import Station, Profile, JugSize, JugType, OrderType, PaymentType, StationSetting

class StationSetupEnforcementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        self.client.login(username='testuser', password='testpassword')

    def test_redirect_when_incomplete(self):
        # Ensure no data initially
        self.assertFalse(JugSize.objects.filter(station=self.station).exists())
        self.assertFalse(JugType.objects.filter(station=self.station).exists())
        self.assertFalse(OrderType.objects.filter(station=self.station).exists())
        self.assertFalse(PaymentType.objects.filter(station=self.station).exists())

        # Try to access Station Setting Detail
        response = self.client.get(reverse('wrsm_app:station-setting-detail'))
        self.assertRedirects(response, reverse('wrsm_app:setup-wizard'))

        # Try to access Add Station Settings
        response = self.client.get(reverse('wrsm_app:add-station-settings'))
        self.assertRedirects(response, reverse('wrsm_app:setup-wizard'))

        # Try to access Station Setting Update
        # Note: StationSettingUpdateView creates the object if it doesn't exist, but Mixin should catch it first
        response = self.client.get(reverse('wrsm_app:station-setting-update'))
        self.assertRedirects(response, reverse('wrsm_app:setup-wizard'))

    def test_access_when_complete(self):
        # Add required data
        JugSize.objects.create(station=self.station, size_label='L', size_in_liters=1)
        JugType.objects.create(station=self.station, jug_type='round')
        OrderType.objects.create(station=self.station, type='Delivery')
        PaymentType.objects.create(station=self.station, name='Cash')

        # Create StationSetting to avoid 404 in DetailView (if it expects it) 
        # Actually StationSettingDetail might expect it or handle None.
        # Let's check the view... it handles DoesNotExist and sets station_settings = None.
        # But StationSettingDetail uses `get_context_data` only, doesn't use `get_object` (TemplateView).
        # However, StationSettingUpdateView creates it.
        
        # Access Station Setting Detail
        response = self.client.get(reverse('wrsm_app:station-setting-detail'))
        self.assertEqual(response.status_code, 200)

        # Access Station Setting Update
        response = self.client.get(reverse('wrsm_app:station-setting-update'))
        self.assertEqual(response.status_code, 200)