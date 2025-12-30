from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from wrsm_app.models import Station, Profile, JugSize, JugType, OrderType, PaymentType, StationSetting, Customer, Product, Sales
from account.models import StationSubscription, SubscriptionPlan
from django.utils import timezone

class OfflineSyncTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        # Setup Master Data
        self.jug_size = JugSize.objects.create(station=self.station, size_label='20L', size_in_liters=20, unit_price=25)
        self.jug_type = JugType.objects.create(station=self.station, jug_type='Round')
        self.order_type = OrderType.objects.create(station=self.station, type='Walk-in', unit_price=0)
        self.payment_type = PaymentType.objects.create(station=self.station, name='Cash')
        
        self.customer = Customer.objects.create(station=self.station, name='Offline Customer')
        self.product = Product.objects.create(
            station=self.station, 
            product_type='REFILL', 
            product_name='Water Refill',
            jug_size=self.jug_size,
            jug_type=self.jug_type,
            unit_price=25
        )
        
        self.station_setting = StationSetting.objects.create(
            station=self.station,
            default_delivery_rate=0,
            default_unit_price=25,
            default_minimum_delivery_qty=1
        )

        # Create Valid Subscription
        self.plan = SubscriptionPlan.objects.create(name='Test Plan', price=100.00)
        StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )

        self.client.login(username='testuser', password='testpassword')

    def test_add_sales_offline_payload(self):
        """
        Test if the server accepts the flattened payload format 
        that offline_forms.js sends via URLSearchParams.
        """
        url = reverse('wrsm_app:add-sales')
        
        # Payload mimicking what syncOfflineRequests constructs
        data = {
            'customer': self.customer.id,
            'order_type': self.order_type.id,
            # 'is_paid': 'on', # Optional
            'note': 'Synced from offline',
            
            # Formset Management Form (Critical)
            'sales_items-TOTAL_FORMS': '1',
            'sales_items-INITIAL_FORMS': '0',
            'sales_items-MIN_NUM_FORMS': '0',
            'sales_items-MAX_NUM_FORMS': '1000',
            
            # Item 0
            'sales_items-0-product': self.product.id,
            'sales_items-0-quantity': '2',
            'sales_items-0-unit_price': '25.00',
            'sales_items-0-total': '50.00',
            'sales_items-0-note': 'Refill',
            'sales_items-0-DELETE': '', # Empty or not present
        }
        
        response = self.client.post(url, data)
        
        # Expect redirect on success (302)
        if response.status_code != 302:
            print("Form Errors:", response.context['form'].errors if 'form' in response.context else "No form context")
            if 'item_formset' in response.context:
                print("Formset Errors:", response.context['item_formset'].errors)
                print("Non-form Errors:", response.context['item_formset'].non_form_errors())

        self.assertEqual(response.status_code, 302)
        
        # Verify Sales Created
        sales = Sales.objects.filter(customer=self.customer, note='Synced from offline').first()
        self.assertIsNotNone(sales)
        self.assertEqual(sales.sales_items.count(), 1)
        item = sales.sales_items.first()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.total, 50.00)

    def test_add_order_offline_payload(self):
        """
        Test if the server accepts the offline payload for adding orders.
        """
        from wrsm_app.models import Order
        url = reverse('wrsm_app:add-order')

        # Payload mimicking what syncOfflineRequests constructs for add_order_form
        data = {
            'customer': self.customer.id,
            'order_type': self.order_type.id,
            'quantity': '5',
            'note': 'Offline Order',
            'status': 'Pending',
            'created_date': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            # 'is_paid': 'on', # Optional
            # 'payment_type': ... # Optional if paid
        }

        response = self.client.post(url, data)

        # Expect redirect on success (302)
        if response.status_code != 302:
             print("Order Form Errors:", response.context['form'].errors if 'form' in response.context else "No form context")

        self.assertEqual(response.status_code, 302)

        # Verify Order Created
        order = Order.objects.filter(customer=self.customer, note='Offline Order').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.quantity, 5)
        self.assertEqual(order.status, 'Pending')
