from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from wrsm_app.models import Station, Profile, Expense, ExpenseItem
from account.models import StationSubscription, SubscriptionPlan
from django.utils import timezone
from datetime import date

class ExpenseManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        # Create valid subscription
        self.plan = SubscriptionPlan.objects.create(name='Test Plan', price_monthly=100.00)
        StationSubscription.objects.create(
            station=self.station,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )
        
        # Add user to station owner/admin group
        self.admin_group, _ = Group.objects.get_or_create(name='station owner/admin')
        self.user.groups.add(self.admin_group)

        self.client.login(username='admin', password='password')
        
        # Create initial expense
        self.expense = Expense.objects.create(
            station=self.station,
            date=date.today(),
            notes='Initial Note',
            reference_number='REF001'
        )
        self.expense_item = ExpenseItem.objects.create(
            expense=self.expense,
            category='utilities',
            description='Item 1',
            qty=1,
            unit_price=100,
            total_amount=100
        )

    def test_update_expense(self):
        url = reverse('wrsm_app:update-expense', kwargs={'pk': self.expense.pk})
        
        # GET request
        response = self.client.get(url)
        if response.status_code == 302:
            print(f"Redirecting to: {response.url}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_update'])

        # POST request (update)
        data = {
            'date': date.today(),
            'notes': 'Updated Note',
            'reference_number': 'REF001-UPDATED',
            'expense_items-TOTAL_FORMS': '1',
            'expense_items-INITIAL_FORMS': '1',
            'expense_items-MIN_NUM_FORMS': '0',
            'expense_items-MAX_NUM_FORMS': '1000',
            'expense_items-0-id': self.expense_item.pk,
            'expense_items-0-category': 'utilities',
            'expense_items-0-description': 'Updated Item 1',
            'expense_items-0-qty': '2',
            'expense_items-0-unit_price': '100',
            'expense_items-0-total_amount': '200',
        }
        
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('wrsm_app:expenses'))
        
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.notes, 'Updated Note')
        
        self.expense_item.refresh_from_db()
        self.assertEqual(self.expense_item.description, 'Updated Item 1')
        self.assertEqual(self.expense_item.total_amount, 200.0)

    def test_delete_expense(self):
        url = reverse('wrsm_app:delete-expense', kwargs={'pk': self.expense.pk})
        
        # GET request (confirmation page)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wrsm/expense_confirm_delete.html')
        
        # POST request (delete)
        response = self.client.post(url)
        self.assertRedirects(response, reverse('wrsm_app:expenses'))
        
        self.assertFalse(Expense.objects.filter(pk=self.expense.pk).exists())
