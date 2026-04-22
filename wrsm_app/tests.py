from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from wrsm_app.models import Station, Profile, JugSize, JugType, OrderType, PaymentType, StationSetting
from account.models import StationSubscription, SubscriptionPlan
from django.utils import timezone

class StationSetupEnforcementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        # Create a valid subscription
        self.plan = SubscriptionPlan.objects.create(name='Test Plan', price_monthly=100.00)
        StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )

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


class UserManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='password')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        from django.contrib.auth.models import Group
        self.group, _ = Group.objects.get_or_create(name='staff')
        
        # Create a valid subscription
        self.plan = SubscriptionPlan.objects.create(name='Test Plan', price_monthly=100.00)
        StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )
        
        self.client.login(username='owner', password='password')

    def test_add_station_user(self):
        url = reverse('wrsm_app:add-station-user')
        data = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@test.com',
            'password': 'password123',
            'role': self.group.id
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('wrsm_app:station-users'))
        
        # Verify User Created (username should be email)
        new_user = User.objects.get(username='new@test.com')
        self.assertTrue(new_user.check_password('password123'))
        self.assertEqual(new_user.email, 'new@test.com')
        
        # Verify Profile Created
        self.assertTrue(Profile.objects.filter(user=new_user, station=self.station).exists())
        
        # Verify Group
        self.assertIn(self.group, new_user.groups.all())
        
        # Verify Audit Log
        from wrsm_app.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(action='ADD', target_model='User', station=self.station).exists())

    def test_update_station_user(self):
        # Create user to update
        user_to_update = User.objects.create_user(username='updateuser', email='old@test.com', password='password')
        Profile.objects.create(user=user_to_update, station=self.station)
        
        url = reverse('wrsm_app:update-station-user', kwargs={'pk': user_to_update.pk})
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com',
            'role': self.group.id
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('wrsm_app:station-users'))
        
        user_to_update.refresh_from_db()
        self.assertEqual(user_to_update.first_name, 'Updated')
        self.assertEqual(user_to_update.email, 'updated@test.com')
        self.assertEqual(user_to_update.username, 'updated@test.com')
        
        # Verify Audit Log
        from wrsm_app.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(action='EDIT', target_model='User', station=self.station).exists())

    def test_disable_station_user(self):
        user_to_disable = User.objects.create_user(username='disableuser', email='disable@test.com', password='password')
        Profile.objects.create(user=user_to_disable, station=self.station)
        
        url = reverse('wrsm_app:disable-station-user', kwargs={'pk': user_to_disable.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:station-users'))
        
        user_to_disable.refresh_from_db()
        self.assertFalse(user_to_disable.is_active)
        
        # Verify Audit Log
        from wrsm_app.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(action='EDIT', details__contains='Disabled', target_model='User', station=self.station).exists())

    def test_enable_station_user(self):
        user_to_enable = User.objects.create_user(username='enableuser', email='enable@test.com', password='password', is_active=False)
        Profile.objects.create(user=user_to_enable, station=self.station)
        
        url = reverse('wrsm_app:enable-station-user', kwargs={'pk': user_to_enable.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:station-users'))
        
        user_to_enable.refresh_from_db()
        self.assertTrue(user_to_enable.is_active)
        
        # Verify Audit Log
        from wrsm_app.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(action='EDIT', details__contains='Enabled', target_model='User', station=self.station).exists())


class StationRegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='reguser', password='password')
        self.profile = Profile.objects.create(user=self.user) # No station initially
        self.plan = SubscriptionPlan.objects.create(name='Basic', price_monthly=100)
        self.client.login(username='reguser', password='password')

    def test_register_new_station(self):
        url = reverse('wrsm_app:register-new-station')
        data = {
            'name': 'My New Station',
            'branch': 'Main Branch',
            'plan': self.plan.id
        }
        
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('wrsm_app:station-list'))
        
        # Verify Station Created
        station = Station.objects.get(name='My New Station')
        self.assertEqual(station.branch, 'Main Branch')
        
        # Verify Profile Linked
        self.profile.refresh_from_db()
        self.assertIn(station, self.profile.allowed_stations.all())
        
        # Verify Subscription
        sub = StationSubscription.objects.get(station=station)
        self.assertEqual(sub.plan, self.plan)
        self.assertTrue(sub.is_active)

class StationListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='listuser', password='password')
        self.station1 = Station.objects.create(name='Station 1', branch='Branch A')
        self.station2 = Station.objects.create(name='Station 2', branch='Branch B')
        self.profile = Profile.objects.create(user=self.user, station=self.station1)
        self.profile.allowed_stations.add(self.station1)
        self.profile.allowed_stations.add(self.station2)
        
        # Add subscription for template logic
        self.plan = SubscriptionPlan.objects.create(name='Basic', price_monthly=100)
        StationSubscription.objects.create(station=self.station1, plan=self.plan)
        StationSubscription.objects.create(station=self.station2, plan=self.plan)
        
        self.client.login(username='listuser', password='password')

    def test_station_list_view(self):
        url = reverse('wrsm_app:station-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Station 1')
        self.assertContains(response, 'Station 2')
        self.assertContains(response, 'Branch A')
        self.assertContains(response, 'Branch B')