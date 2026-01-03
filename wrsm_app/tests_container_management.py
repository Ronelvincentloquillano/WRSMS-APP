from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from wrsm_app.models import Station, Profile, Customer, ContainerManagement
from account.models import StationSubscription, SubscriptionPlan
from django.utils import timezone

class ContainerManagementManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password')
        # Add to station owner/admin group for authorization
        self.group = Group.objects.create(name='station owner/admin')
        self.user.groups.add(self.group)
        
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

        # Create StationSetting required by ContainerManagementListView
        from wrsm_app.models import StationSetting
        StationSetting.objects.create(
            station=self.station,
            default_delivery_rate=0.0,
            default_unit_price=0.0,
            default_minimum_delivery_qty=0
        )
        
        self.customer = Customer.objects.create(name='Test Customer', station=self.station)
        self.record = ContainerManagement.objects.create(
            station=self.station,
            customer=self.customer,
            balance_from_last_visit=10,
            delivered_container=5,
            returned_empty_container=2,
            new_balance=13,
            created_by=self.profile,
            created_date=timezone.now()
        )
        
        self.client.login(username='admin', password='password')

    def test_update_container_record(self):
        url = reverse('wrsm_app:update-container-record', kwargs={'pk': self.record.pk})
        data = {
            'customer': self.customer.pk,
            'balance_from_last_visit': 13,
            'delivered_container': 10,
            'returned_empty_container': 5,
            'new_balance': 18,
            'note': 'Updated note',
            'created_date': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('wrsm_app:container-management-list'))
        
        self.record.refresh_from_db()
        self.assertEqual(self.record.balance_from_last_visit, 13)
        self.assertEqual(self.record.new_balance, 18)
        self.assertEqual(self.record.note, 'Updated note')
        self.assertEqual(self.record.modified_by, self.profile)

    def test_delete_container_record(self):
        url = reverse('wrsm_app:delete-container-record', kwargs={'pk': self.record.pk})
        # GET should show confirm page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wrsm/container_management_confirm_delete.html')
        
        # POST should delete
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:container-management-list'))
        self.assertFalse(ContainerManagement.objects.filter(pk=self.record.pk).exists())
