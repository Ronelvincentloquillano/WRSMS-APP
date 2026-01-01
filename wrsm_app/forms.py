from django import forms
from django.forms import inlineformset_factory
from django.forms import formset_factory
from datetime import datetime, timedelta
# from django.utils import timezone
from . import models
from django.contrib.auth.models import User, Group
from account.models import SubscriptionPlan


class NewStationRegistrationForm(forms.ModelForm):
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.all(), 
        empty_label="Select Plan",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'
        })
    )

    class Meta:
        model = models.Station
        fields = ['name', 'branch']
        labels = {
            'name': 'Station Name',
            'branch': 'Branch',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'
            }),
            'branch': forms.TextInput(attrs={
                'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'
            }),
        }


class SalesUpdateForm(forms.Form):
    note = forms.CharField(
        max_length=200, 
        label="Note", 
        required=False,
    )
    quantity = forms.IntegerField(
        label="Quantity",
    )


class CreateSalesForm(forms.ModelForm):
    class Meta:
        model = models.Sales
        fields = ['customer','order_type','note','is_paid',]
        exclude = ['created_date','station','total_liters']
        widgets = {
            'is_paid' : forms.CheckboxInput(attrs={'type':'checkbox'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        is_disabled = kwargs.pop('is_disabled', False)
        super().__init__(*args, **kwargs)

        if is_disabled:
            for field in self.fields.values():
                field.disabled = True

        if station:
            try:
                settings = models.StationSetting.objects.get(station=station)
                self.fields['order_type'].queryset = models.OrderType.objects.filter(station=station).order_by('-type')
                self.fields['customer'].queryset = models.Customer.objects.filter(station=station).order_by('name')
                self.fields['order_type'].initial = settings.default_order_type
            except models.StationSetting.DoesNotExist:
                pass


class CreateSalesRetroForm(CreateSalesForm):
    created_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Date"
    )

    class Meta(CreateSalesForm.Meta):
        exclude = ['station', 'total_liters']  # removed created_date from exclude

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['created_date'].initial = datetime.now().strftime('%Y-%m-%dT%H:%M')



class SalesItemForm(forms.ModelForm):
    class Meta:
        model = models.SalesItem
        fields = ['product','quantity','unit_price','total','note',]
        widgets = {
            'product' : forms.Select(attrs={'class':'w-auto'}),
            'quantity' : forms.NumberInput(attrs={'class':'text-xl'}),
            'unit_price' : forms.NumberInput(attrs={'class':'text-xl'}),
            'total' : forms.NumberInput(attrs={'class':'text-xl'}),
        }

    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        is_disabled = kwargs.pop('is_disabled', False)
        super().__init__(*args, **kwargs)
        if is_disabled:
            for field in self.fields.values():
                field.disabled = True
        self.fields['product'].queryset = models.Product.objects.filter(station=station).exclude(product_type='SEAL').order_by(
            'product_type','-jug_size__size_in_liters')
        self.fields['product'].empty_label = "SELECT PRODUCT"


class MandatoryInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        # Check if there is at least one non-deleted form with a product
        non_deleted_forms = 0
        for form in self.forms:
            if not form.cleaned_data.get('DELETE', False) and form.cleaned_data.get('product'):
                non_deleted_forms += 1
        
        if non_deleted_forms < 1:
            raise forms.ValidationError("You must add at least one item.")


SalesItemFormSet = inlineformset_factory(
    models.Sales, 
    models.SalesItem, 
    form=SalesItemForm, 
    extra=1, 
    can_delete=True,
    formset=MandatoryInlineFormSet
)


class CreateSalesFromOrderForm(forms.ModelForm):
    class Meta:
        model = models.Sales
        fields = ['order_type','note','is_paid',]
        exclude = ['created_date','station','total_liters']
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        is_disabled = kwargs.pop('is_disabled', False)
        super().__init__(*args, **kwargs)

        if is_disabled:
            for field in self.fields.values():
                field.disabled = True

        if station:
            try:
                settings = models.StationSetting.objects.get(station=station)
                order_types = models.OrderType.objects.filter(station=station)
                self.fields['order_type'].queryset = models.OrderType.objects.filter(station=station.pk).order_by('-type')
                self.fields['order_type'].initial = settings.default_order_type
            except models.StationSetting.DoesNotExist:
                pass


class SalesItemFromOrderForm(forms.ModelForm):
    class Meta:
        model = models.SalesItem
        fields = ['product','quantity','unit_price','total','note',]

    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        is_disabled = kwargs.pop('is_disabled', False)
        super().__init__(*args, **kwargs)
        if is_disabled:
            for field in self.fields.values():
                field.disabled = True
        self.fields['product'].queryset = models.Product.objects.filter(station=station).exclude(product_type='SEAL').order_by(
            'product_type','-jug_size__size_in_liters')
        self.fields['product'].empty_label = "SELECT PRODUCT"


SalesItemFromOrderFormSet = inlineformset_factory(
    models.Sales, 
    models.SalesItem, 
    form=SalesItemFromOrderForm, 
    extra=1, 
    can_delete=True,
    formset=MandatoryInlineFormSet
)


class CreateStationSettingForm(forms.ModelForm):
    class Meta:
        model = models.StationSetting
        fields = '__all__'
        exclude = ['station',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class CreateMaintenanceForm(forms.ModelForm):
    class Meta:
        model = models.Maintenance
        fields = '__all__'
        exclude = ['station','created_by','modified_by','modified_date',]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class CreateJugTypeForm(forms.ModelForm):
    class Meta:
        model = models.JugType
        fields = '__all__'
        exclude = ['station',]
        widgets = {
            'jug_type':forms.TextInput(attrs={
                'placeholder':'example: slim, or round jug'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['jug_type'].initial = None


class CreateProductForm(forms.ModelForm):
    class Meta:
        model = models.Product
        fields = ['product_type','jug_size','jug_type','product_name','unit_price','quantity']
        exclude = ['station','created_by','modified_by','modified_date',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['jug_size'].queryset = models.JugSize.objects.filter(station=station)
        self.fields['jug_type'].queryset = models.JugType.objects.filter(station=station)


class UpdateProductForm(forms.ModelForm):
    class Meta(CreateProductForm.Meta):
        fields = '__all__'
        

class CreateExpenseForm(forms.ModelForm):
    class Meta:
        model = models.Expense
        fields = '__all__'
        exclude = ['station','recorded_by']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class ExpenseItemForm(forms.ModelForm):
    class Meta:
        model = models.ExpenseItem
        fields = '__all__'
        exclude = ['expense',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)

ExpenseItemFormSet = inlineformset_factory(models.Expense, models.ExpenseItem, form=ExpenseItemForm, extra=1, can_delete=True)


class CreateCustomerForm(forms.ModelForm):
    class Meta:
        model = models.Customer
        fields = '__all__'
        exclude = ['station','created_by','modified_date','modified_by',]
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['default_order_type'].queryset = models.OrderType.objects.filter(station=station)
        self.fields['promo_code'].queryset = models.Promo.objects.filter(station=station)
        self.fields['discount_code'].queryset = models.Discount.objects.filter(station=station)


class UpdateCustomerForm(CreateCustomerForm):
    class Meta(CreateCustomerForm.Meta):
        fields = '__all__'


class CreatePromoForm(forms.ModelForm):
    class Meta:
        model = models.Promo
        fields = '__all__'
        exclude = ['station',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class CreateSizeForm(forms.ModelForm):
    class Meta:
        model = models.JugSize
        fields = ['size_label','size_in_liters','unit_price']
        exclude = ['station',]
        widgets = {
            'size_label':forms.TextInput(attrs={
                'placeholder':'example: 20L or 10L'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class UpdateSizeForm(forms.ModelForm):
    class Meta(CreateSizeForm.Meta):
        fields = '__all__'


class CreateOrderTypeForm(forms.ModelForm):
    class Meta:
        model = models.OrderType
        fields = '__all__'
        exclude = ['station',]
        widgets = {
            'type':forms.TextInput(attrs={
                'placeholder':'eg.: Pickup, or Delivery'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class CreatePaymentTypeForm(forms.ModelForm):
    class Meta:
        model = models.PaymentType
        fields = '__all__'
        exclude = ['station',]
        widgets = {
            'name':forms.TextInput(attrs={
                'placeholder':'eg.: Cash, Gcash, or Maya'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class UpdateOrderTypeForm(forms.ModelForm):
    class Meta(CreateOrderTypeForm.Meta):
        fields = '__all__'


class CreateDiscountForm(forms.ModelForm):
    class Meta:
        model = models.Discount
        fields = '__all__'
        exclude = ['station',]

    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class CreateNetTermsForm(forms.ModelForm):
    class Meta:
        model = models.NetTerms
        fields = '__all__'
        exclude = ['station','created_by',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['terms_label'].widget.attrs.update({'placeholder': 'example: Net 0, Net 15, or Net 30'})


class CreateStationSettingsForm(forms.ModelForm):
    class Meta:
        model = models.StationSetting
        fields = '__all__'
        exclude = ['station',]
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        

class UpdateStationSettingForm(forms.ModelForm):
    class Meta(CreateStationSettingForm.Meta):
        fields = '__all__'
        exclude = ['station','modified_by']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        station = self.instance.station
        self.fields['default_jug_size'].queryset = models.JugSize.objects.filter(station=station)
        self.fields['default_order_type'].queryset = models.OrderType.objects.filter(station=station)
        self.fields['default_payment_type'].queryset = models.PaymentType.objects.filter(station=station)
        self.fields['days_to_filter_saleslist'].label = "Number of days to filter Sales list (0 for all, 1 current day)"

        if 'default_jug_size' or 'default_order_type' in self.data:
            try:
                station = int(self.data.get('station'))
                self.fields['default_jug_size'].queryset = models.JugSize.objects.filter(station=station)
                self.fields['default_order_type'].queryset = models.OrderType.objects.filter(station=station)
                self.fields['default_order_type'].queryset = models.OrderType.objects.filter(station=station)
                self.fields['default_payment_type'].queryset = models.PaymentType.objects.filter(station=station)
            except (ValueError, TypeError):
                pass


class CreateForecastForm(forms.ModelForm):
    class Meta:
        model = models.Forecast
        fields = '__all__'
        exclude = ['station',]
        widgets = {
            'last_order_date':forms.DateTimeInput(attrs={'type':'date'}),
            'next_order_date':forms.DateTimeInput(attrs={'type':'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)


class UpdateForecastForm(forms.ModelForm):
    class Meta(CreateForecastForm.Meta):
        fields = '__all__'


class CreateOrderForm(forms.ModelForm):
    class Meta:
        model = models.Order
        fields = '__all__'
        exclude = ['station','created_by','modified_by']
        widgets = {
            'created_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'is_paid' : forms.CheckboxInput(attrs={'type':'checkbox'}),
            'payment_type': forms.RadioSelect(attrs={'class': 'h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500'}),
            'payment_note': forms.Textarea(attrs={'rows': '2','cols':'auto'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)

        self.fields['created_date'].required = True

        settings = models.StationSetting.objects.get(station=station)
        self.fields['customer'].queryset = models.Customer.objects.filter(station=station.pk).order_by('name')
        self.fields['order_type'].queryset = models.OrderType.objects.filter(station=station.pk).order_by('type')
        self.fields['payment_type'].queryset = models.PaymentType.objects.filter(station=station).order_by('sort_number')
        self.fields['order_type'].initial = 'Delivery'
        self.fields['payment_type'].initial = settings.default_payment_type


class UpdateOrderForm(CreateOrderForm):
    class Meta(CreateOrderForm.Meta):
        fields = '__all__'


class CreatePaymentForm(forms.ModelForm):
    class Meta:
        model = models.Payment
        fields = ['total_paid','payment_type','note',]
        widgets = {
            'payment_type': forms.RadioSelect(attrs={'class': 'h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500'}),
            'note': forms.Textarea(attrs={'rows': '2','cols':'auto'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        settings = models.StationSetting.objects.get(station=station)
        self.fields['payment_type'].queryset = models.PaymentType.objects.filter(station=station)
        self.fields['payment_type'].initial = settings.default_payment_type


class CreatePaymentGenericForm(forms.ModelForm):
    class Meta:
        model = models.PaymentGeneric
        fields = ['total_paid','payment_type','note',]
        widgets = {
            'total_paid': forms.NumberInput(attrs={'class': 'text-xl p-4'}),
            'payment_type': forms.Select(attrs={'class': 'w-full p-2 outline-1 -outline-offset-1 outline-white/10 placeholder:text-slate-500 focus:outline-2 focus:-outline-offset-2 focus:outline-sky-400 border border-slate-400'}),
            'note': forms.TextInput(attrs={'class': 'p-4'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        settings = models.StationSetting.objects.get(station=station)
        self.fields['payment_type'].initial = settings.default_payment_type.pk
        self.fields['payment_type'].queryset = models.PaymentType.objects.filter(station=station)


class CreateContainerManagementForm(forms.ModelForm):
    class Meta:
        model = models.ContainerManagement
        fields = '__all__'
        exclude = ['station','created_by',]
        widgets = {
            'created_date': forms.DateTimeInput(format='%Y-%m-%d',attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = models.Customer.objects.filter(station=station).order_by('name')
        self.fields['created_date'].initial = datetime.now().strftime('%Y-%m-%d %H:%M')


class CreateShortcutForm(forms.ModelForm):
    class Meta:
        model = models.ShortCut
        fields = "__all__"
        exclude = ['created_date','station','created_date','created_by','modified_by','modified_date',]
        widgets = {
            'description' : forms.Textarea(attrs={'rows':'2'}),
        }
    
    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        super().__init__(*args, **kwargs)
        self.fields['order_type'].queryset = models.OrderType.objects.filter(station=station.pk)
        self.fields['product'].queryset = models.Product.objects.filter(station=station)


class UpdateShortcutForm(forms.ModelForm):
    class Meta(CreateShortcutForm.Meta):
        fields = '__all__'


class ArticleForm(forms.ModelForm):
    class Meta:
        model = models.Article
        fields = ['title', 'body']
        widgets = {
            'body': forms.Textarea(attrs={'id': 'markdown-editor'}),
        }


class StationUserCreationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ModelChoiceField(queryset=Group.objects.all(), required=True)
    allowed_stations = forms.ModelMultipleChoiceField(
        queryset=models.Station.objects.none(), 
        required=False, 
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']

    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile'):
             self.fields['allowed_stations'].queryset = user.profile.allowed_stations.all()
             if station:
                 self.fields['allowed_stations'].initial = [station]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            user.groups.add(self.cleaned_data["role"])
        return user


class StationUserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    role = forms.ModelChoiceField(queryset=Group.objects.all(), required=True)
    allowed_stations = forms.ModelMultipleChoiceField(
        queryset=models.Station.objects.none(), 
        required=False, 
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        station = kwargs.pop('station', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.instance.pk:
            current_groups = self.instance.groups.all()
            if current_groups:
                self.fields['role'].initial = current_groups[0]
            if hasattr(self.instance, 'profile'):
                self.fields['allowed_stations'].initial = self.instance.profile.allowed_stations.all()

        if user and hasattr(user, 'profile'):
             self.fields['allowed_stations'].queryset = user.profile.allowed_stations.all()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
             raise forms.ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
            user.groups.clear()
            user.groups.add(self.cleaned_data["role"])
            if hasattr(user, 'profile'):
                user.profile.allowed_stations.set(self.cleaned_data['allowed_stations'])
        return user


class CreateStationForm(forms.ModelForm):


    class Meta:


        model = models.Station


        fields = ['name', 'address', 'contact_number']








class UpdateStationForm(forms.ModelForm):


    class Meta:


        model = models.Station


        fields = ['name', 'address', 'branch', 'contact_number']


        widgets = {


            'name': forms.TextInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'}),


            'address': forms.TextInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'}),


            'branch': forms.TextInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'}),


            'contact_number': forms.TextInput(attrs={'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'}),


        }

