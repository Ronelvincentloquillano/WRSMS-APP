from random import random
import string
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def customer_image_upload_path(instance, filename):
    # Organize uploads by customer ID
    return f'customers/{instance.id}/{filename}'


def station_image_upload_path(instance, filename):
    return f'stations/{instance.station.id}/{filename}'


class Station(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    branch = models.CharField(max_length=100, null=True, blank=True, help_text="Location of this branch")
    address = models.CharField(max_length=100, null=True, blank=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    station_code = models.CharField(max_length=10, unique=True, null=True, blank=True)

    def __str__(self):
        if self.branch:
            return f"{self.name} [{self.branch}]"
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    station = models.ForeignKey(to=Station, on_delete=models.SET_NULL, null=True)
    allowed_stations = models.ManyToManyField(to=Station, related_name='allowed_profiles', blank=True)
    station_code = models.CharField(max_length=10, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.station.name if self.station else 'No Station'})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.station:
            self.allowed_stations.add(self.station)


class PaymentType(models.Model):
    station = models.ForeignKey(to=Station, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    sort_number = models.IntegerField(null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "payment type"
    

class OrderType(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    unit_price = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.type

    class Meta:
        verbose_name_plural = "order type"


class JugType(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    jug_type = models.CharField(max_length=50, null=True, blank=True, default='round')

    def __str__(self):
        return self.jug_type or "Unnamed Jug Type"
    
    class Meta:
        verbose_name_plural = "Jug Type"


class JugSize(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    size_label = models.CharField(max_length=10)
    size_in_liters = models.FloatField(null=True, blank=True)
    unit_price = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.size_label} ({self.size_in_liters}L)"
    
    class Meta:
        verbose_name_plural = "Jug Size"


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = (
        ('REFILL', 'REFILL'),
        ('JUG', 'JUG'),
        ('SEAL', 'SEAL'),
        ('SPARE PART', 'SPARE PART'),
        ('DELIVERY CHARGE', 'DELIVERY CHARGE'),
        ('OTHER', 'OTHER'),
    )
    station = models.ForeignKey(to=Station, null=True, blank=True, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=50, null=True, blank=True, choices=PRODUCT_TYPE_CHOICES)
    product_name = models.CharField(max_length=100, null=True, blank=True)
    jug_size = models.ForeignKey(to=JugSize, null=True, blank=True, on_delete=models.CASCADE)
    jug_type = models.ForeignKey(to=JugType, null=True, blank=True, on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='products_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='product_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        if self.product_name != '':
            return f"{self.product_name}"
        else:
            return f"{self.product_type}"


class Promo(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    promo_code = models.CharField(max_length=20)
    promo_description = models.CharField(max_length=100)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.promo_code
    

class Discount(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    discount_code = models.CharField(max_length=20, null=True, blank=True)
    discount_rate = models.FloatField()
    discount_description = models.CharField(max_length=100)

    def __str__(self):
        return self.discount_code
    

class StationSetting(models.Model):
    station = models.OneToOneField(to=Station, null=True, on_delete=models.CASCADE)
    default_delivery_rate = models.FloatField(null=False, blank=False)
    default_jug_size = models.ForeignKey(to=JugSize, null=True, blank=True, on_delete=models.SET_NULL)
    default_unit_price = models.FloatField(null=False, blank=False)
    default_minimum_delivery_qty = models.IntegerField(null=False, blank=False)
    default_order_type = models.ForeignKey(to=OrderType, null=True, blank=True, on_delete=models.SET_NULL)
    default_payment_type = models.ForeignKey(to=PaymentType, null=True, blank=True, on_delete=models.SET_NULL)
    gcash_account = models.CharField(max_length=50, null=True, blank=True, help_text="Gcash account number for payments")
    gcash_qr_image = models.ImageField(upload_to=station_image_upload_path, blank=True, null=True, help_text="Upload your personal GCash QR code image")
    days_to_filter_saleslist = models.IntegerField(null=True, blank=True, default=1, help_text="Number of days to filter sales list")
    num_of_liters_to_backwash = models.IntegerField(null=True, blank=True)
    num_of_liters_to_change_filter = models.IntegerField(null=True, blank=True)
    auto_deduct_supplies = models.BooleanField(default=False, help_text="Auto deduct supplies when sales is made")
    initial_jug_count = models.IntegerField(null=True, blank=True, default=0)
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='stationsetting_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.station.name}"
    
    class Meta:
        verbose_name_plural = "station setting"
        

class NetTerms(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    terms_label = models.CharField(max_length=50)
    terms_in_days = models.PositiveIntegerField(default=0)
    terms_description = models.CharField(max_length=200, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='netterms_created')

    def __str__(self):
        return self.terms_label

    class Meta:
        verbose_name_plural = "net terms"


class Customer(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    purok = models.CharField(max_length=100, null=True, blank=True)
    brgy = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    note = models.CharField(max_length=100, null=True, blank=True)
    default_order_type = models.ForeignKey(to=OrderType, null=True, blank=True, on_delete=models.CASCADE)
    promo_code = models.ForeignKey(to=Promo, null=True, blank=True, on_delete=models.SET_NULL)
    discount_code = models.ForeignKey(to=Discount, null=True, blank=True, on_delete=models.SET_NULL)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='customers_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='customer_modified_by', 
                                    on_delete=models.SET_NULL)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    net_terms = models.ForeignKey(to=NetTerms, null=True, blank=True, on_delete=models.SET_NULL)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_image = models.ImageField(
        upload_to=customer_image_upload_path,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    created_date = models.DateTimeField(default=timezone.now, null=True, blank=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    order_type = models.ForeignKey(OrderType, null=True, on_delete=models.SET_NULL, default='Delivery')
    quantity = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=100, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_type = models.ForeignKey(to=PaymentType, null=True, blank=True, on_delete=models.SET_NULL)
    payment_note = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True, choices=STATUS_CHOICES, default="Pending")
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.RESTRICT)
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='order_modified_by', 
                                    on_delete=models.SET_NULL)
    

class Sales(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    order_type = models.ForeignKey(OrderType, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=100, null=True, blank=True)
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL)
    is_paid = models.BooleanField(null=True, default=False)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='sales_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='sales_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return '{} - {}'.format(self.created_date, self.customer)
    
    class Meta:
        verbose_name_plural = "sales"
        # managed = False  # Important: Don't let Django try to CREATE/MIGRATE this table
        # db_table = 'sales_payment_view'  # This must match the view name in PostgreSQL


class SalesItem(models.Model):
    sales = models.ForeignKey(to=Sales, related_name='sales_items', on_delete=models.CASCADE)
    product = models.ForeignKey(to=Product, null=True, blank=False, related_name='sales_products', on_delete=models.CASCADE)
    note = models.CharField(max_length=50, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=False, null=False)
    quantity = models.IntegerField(blank=False, null=False)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    total_liters = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.sales} - {self.product}"


class CustomerGeneric(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    sales = models.ForeignKey(to=Sales, null=True, on_delete=models.CASCADE)
    note = models.CharField(max_length=100)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='customer_generic_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='customergeneric_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return F"{self.created_date}"
    

class Maintenance(models.Model):
    MAINTENANCE_TYPE_CHOICES = (
        ('backwash', 'backwash'),
        ('cleaning', 'cleaning'),
        ('filter change', 'filter change'),
        ('repair', 'repair'),
        ('other', 'other'),
    )
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    date = models.DateField()
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    note = models.CharField(max_length=300, null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='maintenance_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='maintenance_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return self.maintenance_type
    

class Expense(models.Model):
    date = models.DateField()
    notes = models.TextField(blank=True)
    reference_number = models.CharField(max_length=50, blank=True)
    recorded_by = models.ForeignKey(to=User, on_delete=models.SET_NULL, null=True, blank=True)
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='expense_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"Expense #{self.pk} on {self.date}"
    

class ExpenseItem(models.Model):
    CATEGORY_CHOICES = [
        ('utilities', 'Utilities'),
        ('salaries', 'Salaries & Wages'),
        ('rent', 'Rent'),
        ('transportation', 'Transportation'),
        ('supplies', 'Supplies'),
        ('repairs', 'Repairs & Maintenance'),
        ('marketing', 'Marketing'),
        ('licenses', 'Licensing & Permits'),
        ('software', 'Software & Tools'),
        ('professional', 'Professional Services'),
        ('bank_fees', 'Bank Fees'),
        ('insurance', 'Insurance'),
        ('misc', 'Miscellaneous'),
    ]
    expense = models.ForeignKey(to=Expense, related_name='expense_items', on_delete=models.CASCADE)
    category = models.CharField(max_length=30, null=True, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=100, null=True, blank=True)
    qty = models.FloatField()
    unit_price = models.FloatField()
    total_amount = models.FloatField()

    def __str__(self):
        return self.description
    
    class Meta:
        verbose_name_plural = "expense item"


class Forecast(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    days_frequency = models.PositiveIntegerField(null=True, blank=True,help_text="Number of days between orders")
    last_order_date = models.DateField(null=True, blank=True)
    next_order_date = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Automatically calculate next_order_date if not set
        if self.last_order_date and self.days_frequency:
            self.next_order_date = self.last_order_date + timedelta(days=self.days_frequency)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - Next Order: {self.next_order_date}"
    

class ContainerInventory(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    created_date = models.DateTimeField(blank=True, null=True)
    customer = models.ForeignKey(to=Customer, null=True, on_delete=models.CASCADE)
    balance_from_last_visit = models.IntegerField(default=0)
    delivered_container = models.IntegerField(default=0)
    returned_empty_container = models.IntegerField(default=0)
    new_balance = models.IntegerField(default=0)
    note = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, on_delete=models.SET_NULL, null=True, related_name='container_inventory_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='containerinventory_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.customer.name} - {self.balance_from_last_visit}"
    
    class Meta:
        verbose_name_plural = "container inventory"


class AccountsReceivable(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    customer = models.ForeignKey(to=Customer, null=True, on_delete=models.CASCADE)
    sales = models.ForeignKey(to=Sales, related_name="ar_records",null=True, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, 
                    choices=(('Pending', 'Pending'), ('Partially Paid', 'Partially Paid'), 
                             ('Paid', 'Paid')), 
                    default='Pending')
    issued_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='ar_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='ar_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.sales.pk} - Balance: {self.total_amount}, Status: {self.status}"

    class Meta:
        verbose_name_plural = "accounts receivable"


class Payment(models.Model):
    customer = models.ForeignKey(to=Customer, related_name='payments', on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.ForeignKey(to=PaymentType, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=100, null=True, blank=True)
    received_by = models.ForeignKey(to=Profile, on_delete=models.SET_NULL, null=True, related_name='payments_received')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='payment_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.customer.name} - {self.total_paid} on {self.payment_date}"
    
    class Meta:
        verbose_name_plural = "payments"


class PaymentGeneric(models.Model):
    sales_id = models.CharField(max_length=10, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.ForeignKey(to=PaymentType, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=100, null=True, blank=True)
    received_by = models.ForeignKey(to=Profile, on_delete=models.SET_NULL, null=True, related_name='generic_payments_received')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='paymentgeneric_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.sales_id} - {self.total_paid} on {self.payment_date}"
    

class PaymentItem(models.Model):
    payment = models.ForeignKey(to=Payment, related_name='payment_items', on_delete=models.CASCADE)
    accounts_receivable = models.ForeignKey(to=AccountsReceivable, related_name='ar_payment_items', null=True, on_delete=models.SET_NULL)
    amount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Payment Item - {self.amount_applied}"

    class Meta:
        verbose_name_plural = "payment items"


class CustomerCredit(models.Model):
    customer = models.ForeignKey(to=Customer, related_name='credits', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source_of_payment = models.ForeignKey(to=Payment, null=True, blank=True, on_delete=models.SET_NULL)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(to=Profile, null=True, on_delete=models.SET_NULL, related_name='credits_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='customercredit_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.customer.name} - Credit: {self.amount} on {self.created_date}"

    class Meta:
        verbose_name_plural = "customer credits"


class ShortCut(models.Model):
    station = models.ForeignKey(to=Station, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order_type = models.ForeignKey(to=OrderType, null=True, blank=True, on_delete=models.SET_NULL)
    is_paid = models.BooleanField(choices=[(True, 'Yes'), (False, 'No')], default=False)
    product = models.ForeignKey(to=Product, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=100, null=True, blank=True)
    prompt_note = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(default=1)
    prompt_quantity = models.BooleanField(default=False)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    is_visible = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(to=Profile, on_delete=models.SET_NULL, null=True, related_name='shortcuts_created')
    modified_date = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(to=Profile, null=True, 
                                    blank=True, related_name='shortcut_modified_by', 
                                    on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "shortcuts"


class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    date_published = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "articles"


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('ADD', 'Add'),
        ('EDIT', 'Edit'),
        ('DELETE', 'Delete'),
    )
    station = models.ForeignKey(to=Station, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50)
    target_object_id = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(to=Profile, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.target_model} by {self.performed_by} on {self.timestamp}"