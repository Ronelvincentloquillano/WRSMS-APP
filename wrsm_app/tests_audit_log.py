from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from wrsm_app.models import Station, Profile, Sales, SalesItem, Product, JugSize, JugType, OrderType, PaymentType, StationSetting, AuditLog, Customer
from account.models import StationSubscription, SubscriptionPlan
from django.utils import timezone

class AuditLogSalesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password')
        # Add to station owner/admin group for authorization
        self.group, _ = Group.objects.get_or_create(name='station owner/admin')
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
        
        # Setup required data for Sales
        self.jug_size = JugSize.objects.create(station=self.station, size_label='20L', size_in_liters=20)
        self.jug_type = JugType.objects.create(station=self.station, jug_type='Round')
        self.order_type = OrderType.objects.create(station=self.station, type='Walk-in', unit_price=0)
        self.payment_type = PaymentType.objects.create(station=self.station, name='Cash')
        
        self.product = Product.objects.create(
            station=self.station,
            product_name='Refill 20L',
            product_type='REFILL',
            jug_size=self.jug_size,
            jug_type=self.jug_type,
            unit_price=25,
            quantity=100
        )
        
        StationSetting.objects.create(
            station=self.station,
            default_delivery_rate=0,
            default_unit_price=25,
            default_minimum_delivery_qty=1,
            default_order_type=self.order_type,
            default_payment_type=self.payment_type,
            default_jug_size=self.jug_size
        )
        
        # Create a Sale
        self.sale = Sales.objects.create(
            station=self.station,
            order_type=self.order_type,
            created_by=self.profile
        )
        SalesItem.objects.create(
            sales=self.sale,
            product=self.product,
            quantity=2,
            unit_price=25,
            total=50
        )
        
        self.client.login(username='admin', password='password')

    def test_delete_sales_audit_log(self):
        url = reverse('wrsm_app:delete-sales', kwargs={'pk': self.sale.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:sales'))
        
        # Check Audit Log
        log = AuditLog.objects.filter(
            action='DELETE', 
            target_model='Sales', 
            target_object_id=str(self.sale.pk),
            station=self.station
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, self.profile)

    def test_update_sales_audit_log(self):
        url = reverse('wrsm_app:update-sales', kwargs={'pk': self.sale.pk})
        
        # Form data for update (needs formset data)
        # Note: In a real update, we usually send back the existing IDs to update them, 
        # or new ones to add. Since we are using extra=0 and standard formset saving:
        # If we don't provide IDs, it might try to create new items. 
        # To update existing, we usually need 'sales_items-0-id'.
        # However, for this test, we just want to verify the view logic runs successfully and creates log.
        # Creating a new item implies updating the Sale record (saving it).
        
        data = {
            'order_type': self.order_type.pk,
            'is_paid': False,
            'sales_items-TOTAL_FORMS': '1',
            'sales_items-INITIAL_FORMS': '0', 
            'sales_items-MIN_NUM_FORMS': '0',
            'sales_items-MAX_NUM_FORMS': '1000',
            
            'sales_items-0-product': self.product.pk,
            'sales_items-0-quantity': 5, # Changed quantity
            'sales_items-0-unit_price': 25,
            'sales_items-0-total': 125,
            'sales_items-0-DELETE': '',
        }
        
        response = self.client.post(url, data)
        
        # If form invalid, it returns 200 with errors.
        if response.status_code == 200:
            print(response.context['form'].errors)
            if 'item_formset' in response.context:
                print(response.context['item_formset'].errors)
                
        self.assertRedirects(response, reverse('wrsm_app:sales'))
        
        # Check Audit Log
        log = AuditLog.objects.filter(
            action='EDIT', 
            target_model='Sales', 
            target_object_id=str(self.sale.pk),
            station=self.station
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, self.profile)

class AuditLogCustomerTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin_cust', password='password')
        # Ensure group exists or get it if it was created in previous tests (tests run in isolation usually)
        self.group, _ = Group.objects.get_or_create(name='station owner/admin')
        self.user.groups.add(self.group)
        
        self.station = Station.objects.create(name='Test Station Cust')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        self.plan = SubscriptionPlan.objects.create(name='Test Plan Cust', price_monthly=100.00)
        StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )
        
        self.customer = Customer.objects.create(name='Delete Me', station=self.station)
        self.client.login(username='admin_cust', password='password')

    def test_delete_customer_audit_log(self):
        url = reverse('wrsm_app:delete-customer', kwargs={'pk': self.customer.pk})
        # View expects POST for actual deletion
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:customers'))
        
        # Check Audit Log
        log = AuditLog.objects.filter(
            action='DELETE', 
            target_model='Customer', 
            target_object_id=str(self.customer.pk),
            station=self.station
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Delete Me", log.details)
        self.assertEqual(log.performed_by, self.profile)
