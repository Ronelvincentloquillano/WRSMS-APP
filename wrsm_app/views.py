import json
import logging
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect

logger = logging.getLogger(__name__)
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Max, F, ExpressionWrapper, DecimalField, Count, Q
from collections import defaultdict
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DetailView, DeleteView
from django.forms import inlineformset_factory
from . import models
from . import forms

# global variables
today = timezone.now()
local_date = today.astimezone(timezone.get_current_timezone()).date()
current_date = today.date()

class StationSetupRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        station = request.user.profile.station
        if not (
            models.JugSize.objects.filter(station=station).exists() and
            models.JugType.objects.filter(station=station).exists() and
            models.OrderType.objects.filter(station=station).exists() and
            models.PaymentType.objects.filter(station=station).exists()
        ):
            messages.warning(request, "Please complete the setup wizard before accessing Station Settings.")
            return redirect('wrsm_app:setup-wizard')
        return super().dispatch(request, *args, **kwargs)

@login_required
def setup_wizard(request):
    station = request.user.profile.station
    
    # Check existing data
    jug_sizes = models.JugSize.objects.filter(station=station)
    jug_types = models.JugType.objects.filter(station=station)
    order_types = models.OrderType.objects.filter(station=station)
    payment_types = models.PaymentType.objects.filter(station=station)
    
    jug_sizes_count = jug_sizes.count()
    jug_types_count = jug_types.count()
    order_types_count = order_types.count()
    payment_types_count = payment_types.count()

    # Initialize forms
    jug_size_form = forms.CreateSizeForm(station=station)
    jug_type_form = forms.CreateJugTypeForm(station=station)
    order_type_form = forms.CreateOrderTypeForm(station=station)
    payment_type_form = forms.CreatePaymentTypeForm(station=station)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'jug_size':
            jug_size_form = forms.CreateSizeForm(request.POST, station=station)
            if jug_size_form.is_valid():
                instance = jug_size_form.save(commit=False)
                instance.station = station
                instance.save()
                messages.success(request, "Jug Size added!")
                return redirect('wrsm_app:setup-wizard')
                
        elif form_type == 'jug_type':
            jug_type_form = forms.CreateJugTypeForm(request.POST, station=station)
            if jug_type_form.is_valid():
                instance = jug_type_form.save(commit=False)
                instance.station = station
                instance.save()
                messages.success(request, "Jug Type added!")
                return redirect('wrsm_app:setup-wizard')

        elif form_type == 'order_type':
            order_type_form = forms.CreateOrderTypeForm(request.POST, station=station)
            if order_type_form.is_valid():
                instance = order_type_form.save(commit=False)
                instance.station = station
                instance.save()
                messages.success(request, "Order Type added!")
                return redirect('wrsm_app:setup-wizard')

        elif form_type == 'payment_type':
            payment_type_form = forms.CreatePaymentTypeForm(request.POST, station=station)
            if payment_type_form.is_valid():
                instance = payment_type_form.save(commit=False)
                instance.station = station
                instance.save()
                messages.success(request, "Payment Type added!")
                return redirect('wrsm_app:setup-wizard')

    is_complete = (jug_sizes_count > 0 and jug_types_count > 0 and 
                   order_types_count > 0 and payment_types_count > 0)

    context = {
        'jug_sizes': jug_sizes,
        'jug_types': jug_types,
        'order_types': order_types,
        'payment_types': payment_types,
        'jug_sizes_count': jug_sizes_count,
        'jug_types_count': jug_types_count,
        'order_types_count': order_types_count,
        'payment_types_count': payment_types_count,
        'jug_size_form': jug_size_form,
        'jug_type_form': jug_type_form,
        'order_type_form': order_type_form,
        'payment_type_form': payment_type_form,
        'is_complete': is_complete
    }
    
    return render(request, 'wrsm/setup_wizard.html', context)


def index(request):
    if request.user.is_authenticated:
        return redirect('wrsm_app:dashboard')
    return render(request, 'index.html')


@login_required
def switch_station(request, station_id):
    user = request.user
    profile = user.profile
    try:
        new_station = models.Station.objects.get(id=station_id)
        if new_station in profile.allowed_stations.all():
            profile.station = new_station
            profile.save()
            messages.success(request, f"Switched to station: {new_station.name}")
        else:
            messages.error(request, "You do not have permission to access this station.")
    except models.Station.DoesNotExist:
        messages.error(request, "Station not found.")
    
    return redirect('wrsm_app:dashboard')


@login_required
def dashboard(request):
    user = request.user
    station = getattr(user.profile, 'station', None)
    station_settings = models.StationSetting.objects.get(station=station)
    last_backwash = models.Maintenance.objects.filter(
        station=station,
        maintenance_type='backwash'
    ).last()
    last_filter_change = models.Maintenance.objects.filter(
        station=station,
        maintenance_type='filter change'
    ).last()
    slim_seals = models.Product.objects.filter(
            station=station,
            product_type='SEAL',
        ).exclude(jug_type__jug_type__in=['round'])
    umbrella_seals = models.Product.objects.filter(
            station=station,
            product_type='SEAL',
            jug_type__jug_type__in=['round']
        ).aggregate(total=Sum('quantity'))['total'] or 0
    if last_backwash:
        start_date = last_backwash.date + timedelta(days=1)
    else:
        start_date = None
    end_date = today
    total_liters = 0
    transactions = []

    if start_date:
        try:
            transactions = models.SalesItem.objects.filter(sales__created_date__date__range=[start_date, end_date]).order_by('-sales__created_date')
            total_liters = transactions.aggregate(total=Sum('total_liters'))['total'] or 0
        except ValueError:
            pass  # Invalid date format

    # Chart Data
    # 1. Forecast
    forecasts = models.Forecast.objects.filter(station=station)
    today_forecast_count = forecasts.filter(next_order_date=current_date).count()
    total_forecast_count = forecasts.count()
    rest_forecast_count = max(0, total_forecast_count - today_forecast_count)

    # 2. Container Inventory
    inventory_qs = models.ContainerInventory.objects.filter(station=station)
    customers_with_inventory = inventory_qs.values_list('customer', flat=True).distinct()
    loaned_jugs = 0
    for cust_id in customers_with_inventory:
        try:
            latest = inventory_qs.filter(customer_id=cust_id).latest('created_date')
            loaned_jugs += latest.new_balance
        except models.ContainerInventory.DoesNotExist:
            pass
    
    initial_jug_count = station_settings.initial_jug_count or 0
    remaining_jugs = max(0, initial_jug_count - loaned_jugs)

    # 3. Products
    products = models.Product.objects.filter(station=station).exclude(product_type='REFILL').exclude(product_type='DELIVERY CHARGE')
    
    valid_products = []
    for p in products:
        # Determine the name exactly as it would be displayed
        name = p.product_name if p.product_name else p.product_type
        
        # rigorous check: must be truthy, not just whitespace, and not literally "undefined"
        if name and str(name).strip() and str(name).strip().lower() != 'undefined':
            valid_products.append(p)

    product_names = [(p.product_name if p.product_name else p.product_type) for p in valid_products]
    product_quantities = [p.quantity or 0 for p in valid_products]

    # 4. Sales vs Expenses (Monthly)
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    sales_agg = models.SalesItem.objects.filter(
        sales__station=station, 
        sales__created_date__gte=current_month_start
    ).aggregate(total=Sum('total'))
    sales_total = sales_agg['total'] if sales_agg['total'] is not None else 0
    
    expenses_agg = models.ExpenseItem.objects.filter(
        expense__station=station, 
        expense__date__gte=current_month_start
    ).aggregate(total=Sum('total_amount'))
    expenses_total = expenses_agg['total'] if expenses_agg['total'] is not None else 0

    context = {
        'station': station,
        'last_backwash': last_backwash,
        'last_filter_change': last_filter_change,
        'total_liters': total_liters,
        'transactions': transactions,
        'station_settings': station_settings,
        'slim_seals': slim_seals,
        'umbrella_seals': umbrella_seals,
        'today_forecast_count': today_forecast_count,
        'rest_forecast_count': rest_forecast_count,
        'loaned_jugs': loaned_jugs,
        'remaining_jugs': remaining_jugs,
        'product_names': json.dumps(product_names),
        'product_quantities': json.dumps(product_quantities),
        'sales_total': float(sales_total),
        'expenses_total': float(expenses_total),
    }
    return render(request, 'dashboard.html', context)


@login_required
def home(request):
    user = request.user
    station = getattr(user.profile, 'station', None)
    shortcuts = models.ShortCut.objects.filter(station=station)
    context = {
        'station': station,
        'orders_count': models.Order.objects.filter(
            station=station,status__in=['Pending','In Progress']
            ).order_by('created_date','status').count(),
        'shortcuts': shortcuts
    }
    return render(request, 'home.html', context)


def pricing(request):
    return render(request, 'pricing.html')


def about(request):
    return render(request, 'about.html')


def contact_us(request):
    return render(request, 'contact_us.html')


def custom_logout_view(request):
    logout(request)
    return redirect('/')


@login_required
def add_sales(request):
    station = request.user.profile.station
    station_settings = models.StationSetting.objects.get(station=station)
    user = models.Profile.objects.get(user=request.user)
    

    if request.method == 'POST':
        sales_form = forms.CreateSalesForm(request.POST, station=station)
        item_formset = forms.SalesItemFormSet(request.POST, form_kwargs={'station': station})

        if sales_form.is_valid() and item_formset.is_valid():
            instance = sales_form.save(commit=False)
            instance.station = station
            instance.created_by = user
            instance.save()
            items = item_formset.save(commit=False)
            subtotal = 0
            for item in items:
                item.sales = instance
                item.total = item.unit_price * item.quantity
                if item.product.product_type == "REFILL":
                    slim_seal_product = models.Product.objects.filter(
                        station=station,
                        product_type='SEAL',
                        ).exclude(jug_type__jug_type__in=['round'])
                    round_seal_product = models.Product.objects.filter(
                        station=station,
                        product_type='SEAL',
                        ).exclude(jug_type__jug_type__in=['slim','slim with faucet'])
                    item.total_liters = item.product.jug_size.size_in_liters * item.quantity
                    if item.product.jug_size.size_in_liters >= 10 and item.product.jug_type.jug_type in ['slim','slim with faucet']:
                        for seal in slim_seal_product:
                            seal.quantity -= item.quantity
                            seal.save()
                    if item.product.jug_size.size_in_liters >= 20 and item.product.jug_type.jug_type in ['round']:
                        for seal in round_seal_product:
                            seal.quantity -= item.quantity
                            seal.save()
                subtotal += item.total
                item.save()
            sales_obj = models.Sales.objects.get(pk=instance.pk)

            # no selected customer
            if instance.customer == None:
                return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
            ar_status = "Paid" if instance.is_paid else "Pending"
            ar_obj = models.AccountsReceivable.objects.create(
                station=instance.station,
                customer=instance.customer,
                sales=sales_obj,
                total_amount=subtotal,
                status=ar_status,
                issued_date=today
            )
            if ar_status == "Paid":
                payment_obj = models.Payment.objects.create(
                    customer = sales_obj.customer,
                    total_paid = subtotal,
                    payment_type = None,
                    received_by = request.user.profile,
                )
                models.PaymentItem.objects.create(
                    payment = payment_obj,
                    accounts_receivable = ar_obj,
                    amount_applied = subtotal
                )

            try:
                customer_credit = models.CustomerCredit.objects.filter(
                    customer = sales_obj.customer
                ).latest('created_date')

                if not customer_credit:
                    customer_credit = models.CustomerCredit.objects.create(
                        customer = sales_obj.customer,
                        amount = 0,
                        created_by = request.user.profile,
                        source_of_payment = None
                    )

                else:
                    if customer_credit.amount > 0 and customer_credit.amount > subtotal:
                        cc_balance = customer_credit.amount - subtotal
                        sales_obj.is_paid = True
                        sales_obj.save()
                        ar_obj.status = "Paid"
                        ar_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer = sales_obj.customer,
                            total_paid = subtotal,
                            payment_type = None,
                            note = "Full payment using customer credit",
                            received_by = request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment = payment_obj,
                            accounts_receivable = ar_obj,
                            amount_applied = subtotal
                        )
                        models.CustomerCredit.objects.create(
                            customer = sales_obj.customer,
                            amount = cc_balance,
                            source_of_payment = payment_obj,
                            created_by = request.user.profile
                        )
                        messages.success(request, "Payment successfully posted using customer credit!")
                    elif customer_credit.amount > 0 and customer_credit.amount < subtotal:
                        cc_balance = 0
                        sales_amount_balance = subtotal - customer_credit.amount
                        ar_obj.status = "Partially Paid"
                        ar_obj.save()
                        sales_obj.is_paid = False
                        sales_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer = sales_obj.customer,
                            total_paid = customer_credit.amount,
                            payment_type = None,
                            note = "Partial payment using customer credit",
                            received_by = request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment = payment_obj,
                            accounts_receivable = ar_obj,
                            amount_applied = customer_credit.amount
                        )
                        models.CustomerCredit.objects.create(
                            customer = sales_obj.customer,
                            amount = cc_balance,
                            source_of_payment = payment_obj,
                            created_by = request.user.profile
                        )
                        messages.info(request, F"Payment posted using customer credit balance. Remaining sales amount: {sales_amount_balance}")
                    elif customer_credit.amount > 0 and customer_credit.amount == subtotal:
                        ar_obj.status = "Paid"
                        ar_obj.save()
                        sales_obj.is_paid = True
                        sales_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer = sales_obj.customer,
                            total_paid = subtotal,
                            payment_type = None,
                            note = "Full payment using customer credit",
                            received_by = request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment = payment_obj,
                            accounts_receivable = ar_obj,
                            amount_applied = subtotal
                        )
                        models.CustomerCredit.objects.create(
                            customer = sales_obj.customer,
                            amount = 0,
                            source_of_payment = payment_obj,
                            created_by = request.user.profile
                        )
                        messages.success(request, "Payment successfully posted using customer credit!")
            except models.CustomerCredit.DoesNotExist:
                pass

            return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
            
    else:
        sales_form = forms.CreateSalesForm(station=station)
        item_formset = forms.SalesItemFormSet(form_kwargs={'station': station})
        
    return render(request,'wrsm/add_sales.html',{
        'form':sales_form,
        'item_formset': item_formset,
        'station':station,
        'station_settings':station_settings
        })


@login_required
def add_sales_from_order(request, order_id):
    station = request.user.profile.station
    station_settings = models.StationSetting.objects.get(station=station)
    user = models.Profile.objects.get(user=request.user)
    order_obj = models.Order.objects.get(pk=order_id) if order_id else None
    customer = models.Customer.objects.get(id=order_obj.customer.id) if order_obj.customer else None

    if request.method == 'POST':
        sales_form = forms.CreateSalesFromOrderForm(request.POST, station=station)
        item_formset = forms.SalesItemFromOrderFormSet(request.POST, form_kwargs={'station': station})
        if sales_form.is_valid() and item_formset.is_valid():
            instance = sales_form.save(commit=False)
            instance.station = station
            instance.customer = customer
            instance.created_by = user
            instance.is_paid = order_obj.is_paid
            instance.order = order_obj
            instance.save()
            items = item_formset.save(commit=False)
            subtotal = 0
            for item in items:
                item.sales = instance
                item.total = item.unit_price * item.quantity
                subtotal += item.total
                if item.product.product_type == "REFILL":
                    slim_seal_product = models.Product.objects.filter(
                        station=station,
                        product_type='SEAL',
                        ).exclude(jug_type__jug_type__in=['round'])
                    round_seal_product = models.Product.objects.filter(
                        station=station,
                        product_type='SEAL',
                        ).exclude(jug_type__jug_type__in=['slim','slim with faucet'])
                    item.total_liters = item.product.jug_size.size_in_liters * item.quantity
                    if item.product.jug_size.size_in_liters >= 10 and item.product.jug_type.jug_type in ['slim','slim with faucet']:
                        for seal in slim_seal_product:
                            seal.quantity -= item.quantity
                            seal.save()
                    if item.product.jug_size.size_in_liters >= 20 and item.product.jug_type.jug_type in ['round']:
                        for seal in round_seal_product:
                            seal.quantity -= item.quantity
                            seal.save()
                item.save()

            sales_obj = models.Sales.objects.get(pk=instance.pk)
            is_paid = instance.is_paid

            # no selected customer
            if instance.customer == None:
                if is_paid:
                    if order_obj.note and order_obj.payment_note:
                        note = f"Order#: {order_obj.id} - ({order_obj.payment_type}) {order_obj.payment_note}"
                    elif order_obj.payment_note:
                        note = f"Order#: {order_obj.id} - {order_obj.payment_note}"
                    else:
                        note = f"Order#: {order_obj.id} - {order_obj.note}"
                    models.PaymentGeneric.objects.create(
                        sales_id=sales_obj.pk,
                        total_paid=order_obj.paid_amount,
                        payment_type=order_obj.payment_type,
                        note=note,
                        received_by=request.user.profile,
                    )
                    order_obj.status = "Completed"
                    order_obj.save()
                else:
                    order_obj.status = "Completed"
                    order_obj.save()
                return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))

            ar_obj = models.AccountsReceivable.objects.create(
                station=instance.station,
                customer=order_obj.customer,
                sales=instance,
                total_amount=subtotal,
                status="Pending",
                issued_date=today
            )


            try:
                customer_credit = models.CustomerCredit.objects.filter(
                    customer=order_obj.customer
                ).latest('created_date')

                if not customer_credit:
                    customer_credit = models.CustomerCredit.objects.create(
                        customer=order_obj.customer,
                        amount=0,
                        created_by=request.user.profile,
                        source_of_payment=None
                    )

                else:
                    payment = customer_credit.amount
                    if is_paid:
                        payment = customer_credit.amount + subtotal
                    if payment > 0 and payment > subtotal:
                        cc_balance = payment - subtotal
                        sales_obj.is_paid = True
                        sales_obj.save()
                        ar_obj.status = "Paid"
                        ar_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer=order_obj.customer,
                            total_paid=subtotal,
                            payment_type=None,
                            note="Full payment using customer credit",
                            received_by=request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment=payment_obj,
                            accounts_receivable=ar_obj,
                            amount_applied=subtotal
                        )
                        models.CustomerCredit.objects.create(
                            customer=order_obj.customer,
                            amount=cc_balance,
                            source_of_payment=payment_obj,
                            created_by=request.user.profile
                        )
                        messages.success(request, "Payment successfully posted using customer credit!")
                    elif payment > 0 and payment < subtotal:
                        cc_balance = 0
                        sales_amount_balance = subtotal - payment
                        ar_obj.status = "Partially Paid"
                        ar_obj.save()
                        sales_obj.is_paid = False
                        sales_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer=order_obj.customer,
                            total_paid=payment,
                            payment_type=None,
                            note="Partial payment using customer credit",
                            received_by=request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment=payment_obj,
                            accounts_receivable=ar_obj,
                            amount_applied=payment
                        )
                        models.CustomerCredit.objects.create(
                            customer=order_obj.customer,
                            amount=cc_balance,
                            source_of_payment=payment_obj,
                            created_by=request.user.profile
                        )
                        messages.info(request, F"Payment posted using customer credit balance. Remaining sales amount: {sales_amount_balance}")
                    elif payment > 0 and payment == subtotal:
                        ar_obj.status = "Paid"
                        ar_obj.save()
                        sales_obj.is_paid = True
                        sales_obj.save()
                        payment_obj = models.Payment.objects.create(
                            customer=order_obj.customer,
                            total_paid=subtotal,
                            payment_type=None,
                            note="Full payment using customer credit",
                            received_by=request.user.profile,
                        )
                        models.PaymentItem.objects.create(
                            payment=payment_obj,
                            accounts_receivable=ar_obj,
                            amount_applied=subtotal
                        )
            except models.CustomerCredit.DoesNotExist:
                pass

            if is_paid:
                sales_obj.is_paid = True
                sales_obj.save()
                ar_obj.status = "Paid"
                ar_obj.save()
                payment_obj = models.Payment.objects.create(
                    customer=order_obj.customer,
                    total_paid=subtotal,
                    payment_type=order_obj.payment_type,
                    note=order_obj.payment_note,
                    received_by=request.user.profile,
                )
                models.PaymentItem.objects.create(
                    payment=payment_obj,
                    accounts_receivable=ar_obj,
                    amount_applied=subtotal
                )

            # Update order status to completed
            order_obj.status = "Completed"
            order_obj.save()
            messages.success(request, "Order successfully completed and added to sales list.")
            return HttpResponseRedirect(reverse_lazy('wrsm_app:orders'))

    else:
        if order_obj.note and order_obj.payment_note and order_obj.customer == None:
            note = f"Order#: {order_obj.id} {order_obj.note} - ({order_obj.payment_type}) {order_obj.payment_note}"
        else:
            if order_obj.customer == None:
                note = f"Order#: {order_obj.id} - {order_obj.note}" or f"Order#: {order_obj.id} - {order_obj.payment_note}" or f"Order#: {order_obj.id}"
            else:
                note = ""
        sales_form = forms.CreateSalesFromOrderForm(station=station, initial={
            'order_type': order_obj.order_type,
            'note': note,
            'is_paid': order_obj.is_paid,
        })
        item_formset = forms.SalesItemFromOrderFormSet(form_kwargs={'station': station})

    return render(request,'wrsm/add_sales_from_order.html',{
        'form':sales_form,
        'item_formset': item_formset,
        'station':station,
        'customer': customer,
        'station_settings':station_settings
        })


@login_required
def add_shortcut(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateShortcutForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.created_by = request.user.profile
            instance.save()
            instance.uri = f"/shortcuts/{instance.pk}/"
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:shortcuts'))
    else:
        form = forms.CreateShortcutForm(station=station)

    return render(request,'wrsm/add_shortcut.html',{'form':form,'station':station})


@login_required
def process_shortcut(request, pk):
    station = request.user.profile.station
    shortcut = models.ShortCut.objects.get(id=pk, station=station)
    if shortcut.prompt_note or shortcut.prompt_quantity:
        if request.method == 'POST':
            form = forms.SalesUpdateForm(request.POST)
            if form.is_valid():
                note = form.cleaned_data['note']
                quantity = form.cleaned_data['quantity']
                sales_obj = models.Sales.objects.create(
                    station=station,
                    order_type=shortcut.order_type,
                    is_paid=shortcut.is_paid,
                    note=note
                )
                models.SalesItem.objects.create(
                    sales=sales_obj,
                    product=shortcut.product,
                    quantity=quantity,
                    unit_price=shortcut.unit_price,
                    total=quantity * shortcut.unit_price
                )
                messages.success(request, 'Added successfully!')
                return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
        else:
            form = forms.SalesUpdateForm()
            
        return render(request,'wrsm/sales_update_form.html',{'form':form, 'station':station, 'is_paid':shortcut.is_paid})
    
    else:
        sales_obj = models.Sales.objects.create(
            station=station,
            order_type=shortcut.order_type,
            is_paid=shortcut.is_paid,
        )
        models.SalesItem.objects.create(
            sales=sales_obj,
            product=shortcut.product,
            quantity=shortcut.quantity,
            unit_price=shortcut.unit_price,
            total=shortcut.quantity * shortcut.unit_price
        )
        messages.success(request, 'Added successfully!')
        return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))


@login_required
def add_promo(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreatePromoForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:promos'))
    else:
        form = forms.CreatePromoForm(station=station)
        
    return render(request,'wrsm/add_promo.html',{'form':form,'station':station})


@login_required
def add_product(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateProductForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:products'))
    else:
        form = forms.CreateProductForm(station=station)
        
    return render(request,'wrsm/add_product.html',{'form':form,'station':station})


@login_required
def add_jug_type(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateJugTypeForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:jug-types'))
    else:
        form = forms.CreateJugTypeForm(station=station)
        
    return render(request,'wrsm/add_jug_type.html',{'form':form,'station':station})


@login_required
def delete_promo(request, pk):
    promo = models.Promo.objects.get(id=pk)
    models.Promo.objects.get(id=promo.pk).delete()
    messages.success(request, 'Promo has been deleted!')
    return HttpResponseRedirect(reverse_lazy('wrsm_app:promos'))


def get_customer_data(request):
    customer_id = request.GET.get('id_customer')

    try:
        customer = models.Customer.objects.get(id=customer_id)
        station_setting = models.StationSetting.objects.get(station=customer.station)
        data = {
            'promo_code': customer.promo_code.promo_code if customer.promo_code else None,
            'promo_description': customer.promo_code.promo_description if customer.promo_code else None,
            'discount_code': customer.discount_code.discount_code if customer.discount_code else None,
            'discount_description': customer.discount_code.discount_description if customer.discount_code else None,
            'discount_rate': customer.discount_code.discount_rate if customer.discount_code else None,
            'default_order_type': customer.default_order_type.pk if customer.default_order_type else None,
            'default_ot': customer.default_order_type.type if customer.default_order_type else None,
            'station_default_order_type': station_setting.default_order_type.pk if station_setting.default_order_type else None,
        }
        return JsonResponse(data)
    except models.Customer.DoesNotExist or models.StationSetting.DoesNotExist:
        return JsonResponse({'error': 'Customer or StationSetting not found'}, status=404)


def get_payment_item_data(request):
    sales_id = request.GET.get('sales_id')
    ar = models.AccountsReceivable.objects.get(sales_id=sales_id)
    payment_items = models.PaymentItem.objects.filter(accounts_receivable_id=ar.pk)
    total_payments = 0
    for item in payment_items:
        total_payments += item.amount_applied
    data = {
        'total_payments': total_payments,
    }
    return JsonResponse(data)


def get_ordertype_data(request):
    id_order_type = request.GET.get('id_order_type')
    try:
        order_type = models.OrderType.objects.get(id=id_order_type)
        station_setting = models.StationSetting.objects.get(station=order_type.station)
        data = {
            'ot_unit_price': order_type.unit_price if order_type else None,
            'order_type': order_type.type if order_type else None,
            'sys_default_ot': station_setting.default_order_type.type if station_setting else None,
        }
        return JsonResponse(data)
    except models.OrderType.DoesNotExist:
        return JsonResponse({'error': 'Ordertype not found'}, status=404)


def get_jugsize_data(request):
    jug_size_id = request.GET.get('size')
    try:
        jug_size = models.JugSize.objects.get(id=jug_size_id)
        data = {
            'js_unit_price': jug_size.unit_price if jug_size else None,
        }
        return JsonResponse(data)
    except models.JugSize.DoesNotExist:
        return JsonResponse({'error': 'Jugsize not found'}, status=404)


@login_required
def get_finance_data(request):
    month_str = request.GET.get('month')
    station = request.user.profile.station
    
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
        except ValueError:
             return JsonResponse({'error': 'Invalid date format'}, status=400)
    else:
        # Default to current month
        today = timezone.now()
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)

    sales_total = models.SalesItem.objects.filter(
        sales__station=station, 
        sales__created_date__gte=start_date,
        sales__created_date__lt=end_date
    ).aggregate(total=Sum('total'))['total'] or 0
    
    expenses_total = models.ExpenseItem.objects.filter(
        expense__station=station, 
        expense__date__gte=start_date,
        expense__date__lt=end_date
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    return JsonResponse({
        'sales_total': float(sales_total),
        'expenses_total': float(expenses_total)
    })


@login_required
def get_forecast_data(request):
    date_str = request.GET.get('date')
    station = request.user.profile.station
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
    else:
        target_date = timezone.now().date()
        
    forecasts = models.Forecast.objects.filter(station=station)
    target_forecast_count = forecasts.filter(next_order_date=target_date).count()
    total_forecast_count = forecasts.count()
    rest_forecast_count = max(0, total_forecast_count - target_forecast_count)
    
    return JsonResponse({
        'target_forecast_count': target_forecast_count,
        'rest_forecast_count': rest_forecast_count
    })


def get_product_data(request):
    product_id = request.GET.get('id_product')
    try:
        product = models.Product.objects.get(id=product_id)
        data = {
            'unit_price': product.unit_price if product else None,
            'product_type': product.product_type if product else None,
            'jug_size_in_liters': product.jug_size.size_in_liters if product.jug_size else None
        }
        return JsonResponse(data)
    except models.Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
def customer_map(request):
    station = request.user.profile.station
    customers = models.Customer.objects.filter(
        station=station, 
        latitude__isnull=False, 
        longitude__isnull=False
    )
    
    # Serialize data for the map
    customer_data = []
    for c in customers:
        customer_data.append({
            'name': c.name,
            'lat': c.latitude,
            'lng': c.longitude,
            'url': reverse('wrsm_app:customer-detail', args=[c.pk])
        })
    
    context = {
        'station': station,
        'customers_json': json.dumps(customer_data)
    }
    return render(request, 'wrsm/customer_map.html', context)


@login_required
def delivery_map(request):
    station = request.user.profile.station
    # Filter orders for today
    today_orders = models.Order.objects.filter(
        station=station,
        created_date__date=current_date,
        customer__latitude__isnull=False,
        customer__longitude__isnull=False
    )

    # Serialize data for the map
    orders_data = []
    for o in today_orders:
        orders_data.append({
            'customer': o.customer.name,
            'lat': o.customer.latitude,
            'lng': o.customer.longitude,
            'status': o.status,
            'order_type': str(o.order_type),
            'quantity': o.quantity,
            'note': o.note or o.payment_note,
            'url': reverse('wrsm_app:update-order', args=[o.pk, o.pk]) # Assuming update-order takes pk and order_id based on urls.py
        })
    
    context = {
        'station': station,
        'orders_json': json.dumps(orders_data)
    }
    return render(request, 'wrsm/delivery_map.html', context)


@login_required
def add_customer(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateCustomerForm(request.POST, request.FILES, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            models.Forecast.objects.create(
                customer=instance,
                station=station
            )
            return HttpResponseRedirect(reverse_lazy('wrsm_app:customers'))
    else:
        form = forms.CreateCustomerForm(station=station)
        
    return render(request,'wrsm/add_customer.html',{'form':form,'station':station})


@login_required
def add_size(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateSizeForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:sizes'))
    else:
        form = forms.CreateSizeForm(station=station)
        
    return render(request,'wrsm/add_size.html',{'form':form,'station':station})


@login_required
def add_order_type(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateOrderTypeForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:order-types'))
    else:
        form = forms.CreateOrderTypeForm(station=station)
        
    return render(request,'wrsm/add_order_type.html',{'form':form,'station':station})


@login_required
def add_payment_type(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreatePaymentTypeForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:payment-types'))
    else:
        form = forms.CreatePaymentTypeForm(station=station)
        
    return render(request,'wrsm/add_payment_type.html',{'form':form,'station':station})


@login_required
def add_discount(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateDiscountForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:discounts'))
    else:
        form = forms.CreateDiscountForm(station=station)
        
    return render(request,'wrsm/add_discount.html',{'form':form,'station':station})


@login_required
def add_station_settings(request):
    station = request.user.profile.station
    
    # Check setup completeness
    if not (
        models.JugSize.objects.filter(station=station).exists() and
        models.JugType.objects.filter(station=station).exists() and
        models.OrderType.objects.filter(station=station).exists() and
        models.PaymentType.objects.filter(station=station).exists()
    ):
        messages.warning(request, "Please complete the setup wizard before adding Station Settings.")
        return redirect('wrsm_app:setup-wizard')

    # Check if StationSetting already exists
    if models.StationSetting.objects.filter(station=station).exists():
        return redirect('wrsm_app:station-setting-update')

    if request.method == 'POST':
        form = forms.CreateStationSettingsForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:station-setting-detail'))
    else:
        form = forms.CreateStationSettingsForm(station=station)
        
    return render(request,'wrsm/add_station_setting.html',{'form':form,'station':station})


@login_required
def add_net_terms(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateNetTermsForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.created_by = request.user.profile
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:net-terms'))
    else:
        form = forms.CreateNetTermsForm(station=station)

    return render(request,'wrsm/add_net_terms.html',{'form':form,'station':station})


@login_required
def delete_size(request, pk):
    size = models.JugSize.objects.get(id=pk)
    models.JugSize.objects.get(id=size.pk).delete()
    messages.success(request, 'Size has been deleted!')
    return HttpResponseRedirect(reverse_lazy('wrsm_app:sizes'))


@login_required
def backwash_monitor(request):
    station = request.user.profile.station
    last_backwash = models.Maintenance.objects.filter(
        station=station,
        maintenance_type='backwash'
    ).last()
    if last_backwash:
        last_backwash = last_backwash.date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date') or today.isoformat()  # Default to today's date

    total_liters = 0
    transactions = []

    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = models.SalesItem.objects.filter(sales__created_date__date__range=[start, end]).order_by('-sales__created_date')
            total_liters = transactions.aggregate(total=Sum('total_liters'))['total'] or 0
        except ValueError:
            pass  # Invalid date format

    context = {
        'transactions': transactions,
        'total_liters': total_liters,
        'start_date': start_date,
        'end_date': end_date,
        'station': station,
        'last_backwash_date': last_backwash
    }
    return render(request, 'wrsm/backwash_monitor.html', context)


@login_required
def add_maintenance(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateMaintenanceForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:maintenance'))
    else:
        form = forms.CreateMaintenanceForm(station=station)
        
    return render(request,'wrsm/add_maintenance.html',{'form':form,'station':station})


@login_required
def add_expense(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateExpenseForm(request.POST, station=station)
        item_formset = forms.ExpenseItemFormSet(request.POST, form_kwargs={'station': station})
        if form.is_valid() and item_formset.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.recorded_by = request.user
            instance.save()
            items = item_formset.save(commit=False)
            for item in items:
                item.expense = instance
                item.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:expenses'))
    else:
        form = forms.CreateExpenseForm(station=station, initial={'date':datetime.now().strftime('%Y-%m-%d')})
        item_formset = forms.ExpenseItemFormSet()
        
    return render(request,'wrsm/add_expense.html',{'form':form, 'item_formset':item_formset,
                                                   'station':station})


@login_required
def add_forecast(request, pk):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateForecastForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:forecast-list'))
    else:
        form = forms.CreateForecastForm(station=station)
        
    return render(request,'wrsm/add_forecast.html',{'form':form,'station':station})


@login_required
def add_order(request):
    station = request.user.profile.station
    customers = models.Customer.objects.filter(station=station).order_by('name')
    station_setting = models.StationSetting.objects.get(station=station)
    if request.method == 'POST':
        form = forms.CreateOrderForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.created_by = request.user.profile
            instance.save()
            messages.success(request, 'Order successfully submitted')
            return HttpResponseRedirect(reverse_lazy('wrsm_app:orders'))
        else:
            messages.error(request, 'An error occurred.')

    else:
        form = forms.CreateOrderForm(station=station, 
                                     initial={'order_type':station_setting.default_order_type})
        
    return render(request,'wrsm/add_order.html',{'form':form,'station':station, 'customers':customers})


@login_required
def add_container_inventory(request):
    station = request.user.profile.station
    if request.method == 'POST':
        form = forms.CreateContainerInventoryForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.station = station
            instance.created_by = request.user.profile
            instance.save()
            return HttpResponseRedirect(reverse_lazy('wrsm_app:container-inventory-list'))
    else:
        form = forms.CreateContainerInventoryForm(station=station)
        
    return render(request,'wrsm/add_container_inventory.html',{'form':form,'station':station})


@login_required
def get_container_balance(request):
    customer_id = request.GET.get('id_customer')
    try:
        customer_inventory = models.ContainerInventory.objects.filter(
            customer_id=customer_id).latest('created_date')
        data = {
            'bflv': customer_inventory.new_balance if customer_inventory else None,
        }
        return JsonResponse(data)
    except models.ContainerInventory.DoesNotExist:
        return JsonResponse({'error': 'customer inventory not found'}, status=404)


@login_required
def process_order(request, order_id):
    order_obj = models.Order.objects.get(pk=order_id) if order_id else None
    order_obj.status = "In Progress"
    order_obj.save()
    return HttpResponseRedirect(reverse_lazy('wrsm_app:orders'))


@login_required
def cancel_order(request, order_id):
    order_obj = models.Order.objects.get(pk=order_id) if order_id else None
    order_obj.status = "Cancelled"
    order_obj.save()
    return HttpResponseRedirect(reverse_lazy('wrsm_app:orders'))


@login_required
def add_payment(request, customer_id):
    station = request.user.profile.station
    customer = models.Customer.objects.get(pk=customer_id)
    sales_id_checked = request.GET.getlist('sales-id-checked')

    # section A - showing the total unpaid amount on payment form
    payments = 0
    ar_amount = 0
    if sales_id_checked:
        for id in sales_id_checked:
            sales_obj = models.Sales.objects.get(pk=id)
            ar_obj = models.AccountsReceivable.objects.get(sales=sales_obj)
            payment_items_obj = models.PaymentItem.objects.filter(accounts_receivable=ar_obj)
            ar_amount += ar_obj.total_amount
            for payment in payment_items_obj:
                payments += payment.amount_applied
    total_unpaid_amount = ar_amount - payments
    # end of section A

    if sales_id_checked:
        index = 0
        sales_id_count = len(sales_id_checked)
        payment_balance = 0

        if request.method == 'POST':
            form = forms.CreatePaymentForm(request.POST, station=station)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.customer = customer
                instance.received_by = request.user.profile
                instance.save()

                payment_obj = models.Payment.objects.get(pk=instance.pk)
                payment_balance = payment_obj.total_paid


                for sales_id in sales_id_checked:
                    sales_obj = models.Sales.objects.get(pk=sales_id)
                    ar_obj = models.AccountsReceivable.objects.get(sales=sales_obj)
                    total_payment_obj = models.PaymentItem.objects.filter(accounts_receivable=ar_obj)
                    sales_amount = ar_obj.total_amount # SA
                    total_payments = 0
                    for item in total_payment_obj:
                        total_payments += item.amount_applied
                    total_balance = sales_amount - total_payments

                    # Create a payment item for each sales object
                    if total_balance > 0:
                        if payment_balance > total_balance:
                            # Create a payment item for the remaining amount
                            payment_balance -= total_balance
                            models.PaymentItem.objects.create(
                                payment=payment_obj,
                                accounts_receivable=ar_obj,
                                amount_applied=total_balance
                            )
                            ar_obj.status = "Paid"
                            ar_obj.save()
                            sales_obj.is_paid = True
                            sales_obj.save()
                            index += 1
                            messages.info(request, F"Payment successfully posted.")
                        elif payment_balance < total_balance:
                            remaining_balance = total_balance - payment_balance
                            models.PaymentItem.objects.create(
                                payment=payment_obj,
                                accounts_receivable=ar_obj,
                                amount_applied=payment_balance
                            )
                            payment_balance = 0
                            ar_obj.status = "Partially Paid"
                            ar_obj.save()
                            index += 1
                            messages.info(request, F"Partial payment posted. Remaining balance: {remaining_balance}")
                        else:
                            models.PaymentItem.objects.create(
                                payment=payment_obj,
                                accounts_receivable=ar_obj,
                                amount_applied=payment_balance
                            )
                            payment_balance=0
                            ar_obj.status = "Paid"
                            ar_obj.save()
                            sales_obj.is_paid = True
                            sales_obj.save()
                            index += 1
                            messages.success(request, "Payment successfully posted!")

                    if index == sales_id_count:
                        if payment_balance > 0:
                            models.CustomerCredit.objects.create(
                                customer=customer,
                                amount=payment_balance,
                                source_of_payment=payment_obj,
                                created_by=request.user.profile
                            )
                            messages.info(request, F"An extra payment of {payment_balance} has been credited to customer.")
                        return HttpResponseRedirect(reverse_lazy('wrsm_app:customer-detail', kwargs={'pk': customer_id}))
            
        else:
            form = forms.CreatePaymentForm(station=station)
            
        return render(request, 'wrsm/payment_form.html', 
            {'form': form, 'station': station, 'customer': customer, 
            'total_unpaid_amount': total_unpaid_amount})

    else:
        if request.method == 'POST':
            form = forms.CreatePaymentForm(request.POST, station=station)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.customer = customer
                instance.received_by = request.user.profile
                instance.save()
                models.CustomerCredit.objects.create(
                    customer=instance.customer,
                    amount=instance.total_paid,
                    source_of_payment=instance,
                    created_by=request.user.profile
                )
                messages.success(request, F"A payment of {instance.total_paid} has been successfully posted as customer credit!")
                return HttpResponseRedirect(reverse_lazy('wrsm_app:customer-detail', kwargs={'pk': customer_id}))

        else:
            form = forms.CreatePaymentForm(station=station)

    return render(request, 'wrsm/payment_form.html', 
                {'form': form, 'station': station, 'customer': customer, 
                'total_unpaid_amount': total_unpaid_amount})


@login_required
def add_payment_generic(request, pk, sales_id):
    station = request.user.profile.station
    sales_obj = models.Sales.objects.get(pk=sales_id)
    sales_amount = models.SalesItem.objects.filter(sales_id=sales_id).aggregate(
        total=Sum(ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField()))
    )
    if request.method == 'POST':
        form = forms.CreatePaymentGenericForm(request.POST, station=station)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.sales_id = sales_obj.pk
            instance.received_by = request.user.profile
            instance.save()
            sales_obj.is_paid=True
            sales_obj.save()
            messages.success(request, "Payment successfully posted!")
            return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
    else:
        form = forms.CreatePaymentGenericForm(station=station, initial={'total_paid':sales_amount['total']})

    return render(request, 'wrsm/payment_form_generic.html', 
        {'form': form, 'station': station, 'sales_obj': sales_obj, 'sales_amount': sales_amount})


class OrderUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateOrderForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/update_order.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:orders')
    
    def get_queryset(self, **kwargs):
        return models.Order.objects.filter(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        context.update({
            'station': station,
        })
        return context


class OrderListView(LoginRequiredMixin, ListView):
    model = models.Order
    template_name = 'wrsm/orders.html'

    def get_queryset(self):
        station = self.request.user.profile.station
        queryset = super().get_queryset().filter(station=station)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        selected_filters = self.request.GET.getlist('filter')
        queryset = models.Order.objects.filter(station=station)
        if selected_filters:
            orders = queryset.filter(status__in=selected_filters)
        else:
            orders = queryset.filter(status__in=['Pending','In Progress']).order_by('created_date','status')
        context = {
            'orders': orders,
            'station': station,
            'filter_options': models.Order.STATUS_CHOICES,
            'selected_filters': self.request.GET.getlist('filter'),
        }
        return context


class ShortcutsListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/shortcuts.html'
    model = models.ShortCut
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        shortcuts = models.ShortCut.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'shortcuts': shortcuts,
            'station': station
        }
        return context


class PromoListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/promos.html'
    model = models.Promo
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        promos = models.Promo.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'promos': promos,
            'station': station
        }
        return context


class JugTypeListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/jug_types.html'
    model = models.JugType
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        try:
            station_settings = models.StationSetting.objects.get(station=station)
            # Check for completeness
            required_fields = [
                station_settings.default_delivery_rate,
                station_settings.default_jug_size,
                station_settings.default_unit_price,
                station_settings.default_minimum_delivery_qty,
                station_settings.default_order_type,
                station_settings.default_payment_type
            ]
            settings_complete = all(field is not None for field in required_fields)
        except models.StationSetting.DoesNotExist:
            station_settings = None
            settings_complete = False
        jug_types = models.JugType.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'jug_types': jug_types,
            'station': station,
            'settings_complete': settings_complete
        }
        return context


class NetTermsListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/net_terms.html'
    model = models.NetTerms
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        net_terms = models.NetTerms.objects.filter(station=station)
        station = self.request.user.profile.station
        context = super().get_context_data(**kwargs)
        context = {
            'net_terms': net_terms,
            'station': station
        }
        return context
    

class ProductListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/products.html'
    model = models.Product
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        products = models.Product.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'station': station,
            'products': products,
        }
        return context


class ProductUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateProductForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/update_product.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:products')

    def get_queryset(self, **kwargs):
        return models.Product.objects.filter(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        context.update({
            'station': station,
        })
        return context


class ForecastCustomerUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateForecastForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/forecast_customer_update.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:forecast-list')
    
    def get_queryset(self, **kwargs):
        return models.Forecast.objects.filter(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        context.update({
            'station': station,
        })
        return context
    

class SalesListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/sales_list.html'
    model = models.Sales
    context_object_name = 'sales_list'
    # paginate_by = 5

    def get_queryset(self):
        station = self.request.user.profile.station
        station_settings = models.StationSetting.objects.get(station=station)
        num_of_days_to_filter = station_settings.days_to_filter_saleslist or 0
        queryset = super().get_queryset().filter(station=station)

        selected_date = self.request.GET.get('date')
        selected_customer = self.request.GET.get('customer')
        keyword = self.request.GET.get('keyword')

        if selected_date:
            try:
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_date__date=date_obj)
            except ValueError:
                pass

        if selected_customer:
            queryset = queryset.filter(customer__name__icontains=selected_customer)
        
        if keyword:
            if keyword.isdigit():
                queryset = queryset.filter(id=keyword)
            else:
                queryset = queryset.filter(
                    customer__name__icontains=keyword)

        if not selected_date and not selected_customer and not keyword:
            if num_of_days_to_filter == 1:
                queryset = queryset.prefetch_related('sales_items', 'ar_records').filter(created_date__date__range=(current_date, current_date))
            elif num_of_days_to_filter > 1:
                past_date = local_date - timedelta(days=num_of_days_to_filter-1)
                queryset = queryset.prefetch_related('sales_items', 'ar_records').filter(created_date__date__range=(past_date, current_date))
            else:
                queryset = queryset.prefetch_related('sales_items', 'ar_records').all()

        return queryset.order_by('-created_date__date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        products = models.Product.objects.filter(station=station) or None
        try:
            customers = models.Customer.objects.filter(station=station) or None
        except ValueError:
            pass
        grand_total = self.get_queryset().aggregate(
                grand_total=Sum(ExpressionWrapper(F('sales_items__quantity') * F('sales_items__unit_price'), output_field=DecimalField()))
            )['grand_total'] or 0

        context['grand_total'] = grand_total
        context['station'] = station
        if customers != None:
            context['customers'] = customers.order_by('name')

        # Calculate totals per sales_id
        product_expr = ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField())
        product_totals = models.SalesItem.objects.filter(sales__station=station).values('sales_id') \
            .annotate(total=Sum(product_expr), total_qty=Sum('quantity')).order_by('sales_id')

        # Convert to dictionary { sales_id: total_amount }
        context['totals_by_product'] = {item['sales_id']: item['total'] for item in product_totals}
        context['quantities_by_product'] = {item['sales_id']: item['total_qty'] for item in product_totals}
        context['selected_date'] = self.request.GET.get('date', '')
        context['entered_customer'] = self.request.GET.get('customer', '')
        context['products'] = products.count() if products else 0

        return context
    

class CustomersListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/customers.html'
    model = models.Customer
    context_object_name = 'customers'

    def get_queryset(self):
        queryset = super().get_queryset()
        searched_customer = self.request.GET.get('customer')

        if searched_customer:
            queryset = queryset.filter(name__icontains=searched_customer)
        else:
            queryset = queryset.filter(station=self.request.user.profile.station)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = models.Station.objects.get(pk=self.request.user.profile.station.pk)
        count = models.Customer.objects.filter(station=station).count()
        context['station'] = station
        context['count'] = count
        context['searched_customer'] = self.request.GET.get('customer', '')
        return context
    

class SizesListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/sizes.html'
    model = models.JugSize
    # paginate_by = 3

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        sizes = models.JugSize.objects.filter(station=station).order_by('-size_in_liters')
        context = super().get_context_data(**kwargs)
        context = {
            'sizes': sizes,
            'station': station
        }
        return context


class MaintenanceListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/maintenance.html'
    model = models.Maintenance
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        maintenance = models.Maintenance.objects.filter(station=station).order_by('-date')
        context = super().get_context_data(**kwargs)
        context = {
            'maintenance': maintenance,
            'station': station
        }
        return context


class ExpensesListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/expenses.html'
    model = models.Expense
    # paginate_by = 5

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(station=self.request.user.profile.station)

        year_month = self.request.GET.get('year_month')

        if year_month:
            try:
                year, month = year_month.split('-')
                qyear = int(year)
                qmonth = int(month)
                qs = qs.filter(date__year=qyear, date__month=qmonth)
            except ValueError:
                # fallback if parsing fails
                qs = qs.filter(date__year=today.year, date__month=today.month)
        else:
            qs = qs.filter(date__year=today.year, date__month=today.month)

        return qs.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        item_expr = ExpressionWrapper(F('qty') * F('unit_price'), output_field=DecimalField())
        item_totals = models.ExpenseItem.objects.filter(expense__station=station).values('expense_id') \
            .annotate(total=Sum(item_expr))
        expenses = self.get_queryset()
        total_expenses = expenses.aggregate(Sum('expense_items__total_amount'))
        context = {
            'expenses': expenses,
            'totals_by_items': {item['expense_id']: item['total'] for item in item_totals},
            'total_expenses': total_expenses,
            'station': station
        }
        return context


class PromosListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/promos.html'
    model = models.Promo
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        promos = models.Promo.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'promos': promos,
            'station': station
        }
        return context
    

class OrderTypesListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/order_types.html'
    model = models.OrderType
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        ordertypes = models.OrderType.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'ordertypes': ordertypes,
            'station': station
        }
        return context


class PaymentTypesListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/payment_types.html'
    model = models.PaymentType
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        paymenttypes = models.PaymentType.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'paymenttypes': paymenttypes,
            'station': station
        }
        return context


class DiscountsListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/discounts.html'
    model = models.Discount
    # paginate_by = 5

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        discounts = models.Discount.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        context = {
            'discounts': discounts,
            'station': station
        }
        return context


class StationSettingDetail(StationSetupRequiredMixin,TemplateView):
    template_name = 'wrsm/station_setting_detail.html'

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        try:
            station_settings = models.StationSetting.objects.get(station=station)
            # Check for completeness
            required_fields = [
                station_settings.default_delivery_rate,
                station_settings.default_jug_size,
                station_settings.default_unit_price,
                station_settings.default_minimum_delivery_qty,
                station_settings.default_order_type,
                station_settings.default_payment_type
            ]
            settings_complete = all(field is not None for field in required_fields)
        except models.StationSetting.DoesNotExist:
            station_settings = None
            settings_complete = False

        context = super().get_context_data(**kwargs)
        context = {
            'station': station,
            'station_settings': station_settings,
            'settings_complete': settings_complete,
        }
        return context


class CustomerDetail(LoginRequiredMixin, TemplateView):
    template_name = 'wrsm/customer_detail.html'

    def get_context_data(self, **kwargs):
        customer = models.Customer.objects.get(id=self.kwargs['pk'])
        station = self.request.user.profile.station
        context = super().get_context_data(**kwargs)
        customer_order_history = models.Sales.objects.prefetch_related('sales_items','ar_records').filter(customer=customer).order_by('-created_date')
        product_expr = ExpressionWrapper(F('sales_items__quantity') * F('sales_items__unit_price'), output_field=DecimalField())
        product_totals = customer_order_history.values('id').annotate(total=Sum(product_expr))
        try:
            credit = models.CustomerCredit.objects.filter(customer=customer).latest('created_date')
        except models.CustomerCredit.DoesNotExist:
            credit = None
        ar_records = models.AccountsReceivable.objects.prefetch_related('ar_payment_items').filter(customer=customer).order_by('-issued_date')
        context = {
            'customer': customer,
            'customer_order_history': customer_order_history,
            'ar_records': ar_records,
            'credit': credit,
            'product_totals': {item['id']: item['total'] for item in product_totals},
            'station': station,
        }
        return context
    

class CustomerUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateCustomerForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/update_customer.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:customer-detail', kwargs={'pk' : self.object.pk})

    def get_queryset(self, **kwargs):
        return models.Customer.objects.filter(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = models.Customer.objects.get(id=self.kwargs['pk'])
        station = self.request.user.profile.station
        context.update({
            'customer': customer,
            'station': station,
        })
        return context


class StationSettingUpdateView(StationSetupRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateStationSettingForm
    success_message = 'Station Settings successfully updated!'
    template_name = 'wrsm/update_station_setting.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:station-setting-detail')
    
    def get_object(self, queryset=None):
        obj, created = models.StationSetting.objects.get_or_create(
            station=self.request.user.profile.station,
            defaults={
                'default_delivery_rate': 0,
                'default_unit_price': 0,
                'default_minimum_delivery_qty': 0
            }
        )
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        context.update({
            'station': station,
        })
        return context


class SizeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateSizeForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/update_size.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:size-detail', kwargs={'pk' : self.object.pk})


class ForecastListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/forecast.html'
    model = models.Forecast

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        forecast = models.Forecast.objects.filter(station=station).order_by('-next_order_date')
        context = super().get_context_data(**kwargs)
        context = {
            'forecast': forecast,
            'station': station
        }
        return context


class ContainerInventoryListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/container_inventory_list.html'
    model = models.ContainerInventory
    # paginate_by = 10

    def get_context_data(self, **kwargs):
        station = self.request.user.profile.station
        station_setting = models.StationSetting.objects.get(station=station)
        inventory = models.ContainerInventory.objects.filter(station=station)
        context = super().get_context_data(**kwargs)
        loaned_jugs = 0
        customers = inventory.distinct('customer__name')
        for customer in customers:
            latest_record = inventory.filter(
                customer=customer.customer
            ).latest('created_date').new_balance
            loaned_jugs += latest_record if latest_record else 0
        
        inventory = inventory.order_by('customer', '-created_date').distinct('customer')

        searched_customer = self.request.GET.get('customer')
        if searched_customer:
            inventory = models.ContainerInventory.objects.filter(station=station, customer__name__icontains=searched_customer).order_by('-created_date')[:10]
        context = {
            'inventory': inventory,
            'station': station,
            'searched_customer': self.request.GET.get('customer', ''),
            'customers': models.ContainerInventory.objects.filter(station=station).distinct('customer__name'),
            'loaned_jugs': loaned_jugs,
            'initial_jug_count': station_setting.initial_jug_count or 0
        }
        return context


class ARListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/accounts_receivable_list.html'
    model = models.AccountsReceivable
    # paginate_by = 5

    def get_queryset(self, **kwargs):
        station = self.request.user.profile.station
        return models.AccountsReceivable.objects.filter(station=station,status__in=['Pending','Partially Paid'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        ar_items = self.get_queryset()
        selected_filters = self.request.GET.getlist('filter')
        searched_customer = self.request.GET.get('customer')
        if selected_filters:
            ar_items = models.AccountsReceivable.objects.filter(status__in=selected_filters)
        if searched_customer:
            ar_items = models.AccountsReceivable.objects.filter(
                station=station,
                customer__name__icontains=searched_customer).order_by('status')
        if not selected_filters and not searched_customer:
            ar_items = self.get_queryset()
        grand_total = ar_items.aggregate(total=Sum('total_amount'))['total']
        context = {
            'ar_items': ar_items,
            'station': station,
            'selected_filters': self.request.GET.getlist('filter', ''),
            'searched_customer': self.request.GET.get('customer', ''),
            'grand_total': grand_total,
        }
        return context
    

class ShortcutUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = forms.UpdateShortcutForm
    success_message = 'successfully updated!'
    template_name = 'wrsm/update_shortcut.html'

    def get_success_url(self):
        return reverse_lazy('wrsm_app:shortcuts')

    def get_queryset(self, **kwargs):
        return models.ShortCut.objects.filter(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station = self.request.user.profile.station
        context.update({
            'station': station,
        })
        return context
    

@login_required
def update_forecast(request):
    station = request.user.profile.station
    customers = models.Forecast.objects.filter(station=station)
    for customer in customers:
        last_order_date = models.Sales.objects.filter(customer=customer.customer).aggregate(
            latest=Max('created_date')
        )['latest']
        customer.last_order_date = last_order_date
        customer.save()
    
    customer_forecast_list = models.Forecast.objects.filter(station=station)
    for item in customer_forecast_list:
        customer_order_data = models.Sales.objects.filter(customer=item.customer).order_by('created_date')
        try:
            customer = models.Forecast.objects.get(customer=item.customer)
            average_gap_days = 0
            order_dates = []
            order_dates_str = []

            for order in customer_order_data:
                order_dates.append(order.created_date)
                order_dates_str.append(str(order.created_date))

            od_len = len(order_dates)
            gaps = [(order_dates[x] - order_dates[x - 1]).days for x in range(1, od_len)]
            average_gap_days = sum(gaps) / len(gaps) if gaps else 0
            average_gap_days = round(average_gap_days)
            print(item.customer, "customer id:",item.customer.pk, "average:",average_gap_days)
            customer.days_frequency = int(average_gap_days)
            customer.save()
        except models.Forecast.DoesNotExist:
            print(f"Forecast for customer {item.customer.pk} does not exist.")
        
    messages.success(request, "Forecast updated!")

    return redirect('wrsm_app:order-forecast')


@login_required
def monthly_financial_report(request):
    station = request.user.profile.station
    customers = models.Customer.objects.filter(station=station)
    # Group sales by month
    monthly_sales = (
        models.SalesItem.objects.filter(sales__station=station)
        .annotate(month=TruncMonth('sales__created_date__date'))
        .values('month')
        .annotate(total_sales=Sum('total'))
        .order_by('month')
    )

    # Group expenses by month
    monthly_expenses = (
        models.ExpenseItem.objects.filter(expense__station=station)
        .annotate(month=TruncMonth('expense__date'))
        .values('month')
        .annotate(total_expenses=Sum('total_amount'))
        .order_by('month')
    )

    monthly_liters = (
        models.SalesItem.objects.filter(sales__station=station)
        .annotate(month=TruncMonth('sales__created_date__date'))
        .values('month')
        .annotate(total_liters=Sum('total_liters'))
        .order_by('month')
    )
    
    monthly_transactions = (
        models.Sales.objects.filter(station=station)
        .annotate(month=TruncMonth('created_date__date'))
        .values('month').annotate(total_transactions=Count('id'))
        .order_by('month')
    )

    # Combine the data by month
    report = {}
    for sale in monthly_sales:
        report[sale['month']] = {
            'month': sale['month'],
            'total_sales': sale['total_sales'],
            'total_expenses': 0,
            'total_liters': 0,
            'total_transactions': 0
        }
    
    for expense in monthly_expenses:
        if expense['month'] in report:
            report[expense['month']]['total_expenses'] = expense['total_expenses']
        else:
            report[expense['month']] = {
                'month': expense['month'],
                'total_sales': 0,
                'total_expenses': expense['total_expenses'],
                'total_liters': 0,
                'total_transactions': 0
            }

    for liter in monthly_liters:
        if liter['month'] in report:
            report[liter['month']]['total_liters'] = liter['total_liters']
        else:
            report[liter['month']] = {
                'month': liter['month'],
                'total_sales': 0,
                'total_expenses': 0,
                'total_liters': liter['total_liters'],
                'total_transactions': 0
            }
    
    for transaction in monthly_transactions:
        if transaction['month'] in report:
            report[transaction['month']]['total_transactions'] = transaction['total_transactions']
        else:
            report[transaction['month']] = {
                'month': transaction['month'],
                'total_sales': 0,
                'total_expenses': 0,
                'total_liters': 0,
                'total_transactions': transaction['total_transactions']
            }

    # Sort by month
    monthly_report = sorted(report.values(), key=lambda x: x['month'])

    return render(request, 'wrsm/financial_report.html', {'monthly_report': monthly_report, 
                                                        'station': station, 'customers': customers})


def documentation(request):
    query = request.GET.get('q')
    if query:
        articles = models.Article.objects.filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        ).order_by('-date_published')
    else:
        articles = models.Article.objects.all().order_by('-date_published')
    
    return render(request, 'documentation.html', {'articles': articles, 'query': query})


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class ManageArticlesView(AdminRequiredMixin, ListView):
    model = models.Article
    template_name = 'wrsm_app/manage_articles.html'
    context_object_name = 'articles'
    ordering = ['-date_published']

class AddArticleView(AdminRequiredMixin, CreateView):
    model = models.Article
    form_class = forms.ArticleForm
    template_name = 'wrsm_app/article_form.html'
    success_url = reverse_lazy('wrsm_app:manage-articles')

class UpdateArticleView(AdminRequiredMixin, UpdateView):
    model = models.Article
    form_class = forms.ArticleForm
    template_name = 'wrsm_app/article_form.html'
    success_url = reverse_lazy('wrsm_app:manage-articles')


class ArticleDetailView(DetailView):
    model = models.Article
    template_name = 'wrsm_app/article_detail.html'
    context_object_name = 'article'


@login_required
def delete_sales(request, pk):
    # Authorization: Ensure user is linked to a station and is in the 'station owner/admin' group
    is_authorized = request.user.is_superuser or request.user.groups.filter(name='station owner/admin').exists()
    
    if not is_authorized:
         messages.error(request, "Access denied. Requires 'station owner/admin' privileges.")
         return redirect('wrsm_app:sales')

    station = request.user.profile.station if hasattr(request.user, 'profile') else None
    
    # Allow superusers to delete any sale, otherwise filter by station
    if request.user.is_superuser:
        sale = get_object_or_404(models.Sales, pk=pk)
    else:
        # Still enforce station boundary even for group members
        if not station:
             messages.error(request, "No station associated with your profile.")
             return redirect('wrsm_app:sales')
        sale = get_object_or_404(models.Sales, pk=pk, station=station)

    if request.method == 'POST':
        # Audit Logging
        logger.info(f"User {request.user.username} (ID: {request.user.id}) initiated deletion of Sales ID: {sale.pk}")

        try:
            # Manual Cascade for Weakly Linked Records (Payment -> AccountsReceivable)
            ar_records = sale.ar_records.all()
            for ar in ar_records:
                payment_items = ar.ar_payment_items.all()
                for item in payment_items:
                    payment = item.payment
                    item.delete() # Delete the link
                    
                    # If payment has no other items, delete the payment record itself
                    if not payment.payment_items.exists():
                        payment.delete()
                        logger.info(f"Deleted orphaned Payment ID: {payment.pk}")

            # Delete the Sales record (cascades to SalesItems, AR)
            sale.delete()
            messages.success(request, 'Sales record and related payments deleted successfully.')
            logger.info(f"Successfully deleted Sales ID: {pk}")
        except Exception as e:
            logger.error(f"Error deleting Sales ID {pk}: {e}")
            messages.error(request, "An error occurred while deleting the record.")
            
        return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
        
    return render(request, 'wrsm/sales_confirm_delete.html', {'object': sale})


@login_required
def update_sales(request, pk):
    # Authorization: Ensure user is linked to a station and is in the 'station owner/admin' group
    is_authorized = request.user.is_superuser or request.user.groups.filter(name='station owner/admin').exists()

    if not is_authorized:
         messages.error(request, "Access denied. Requires 'station owner/admin' privileges.")
         return redirect('wrsm_app:sales')

    station = request.user.profile.station if hasattr(request.user, 'profile') else None
    
    # Allow superusers to update any sale, otherwise filter by station
    if request.user.is_superuser:
        sale = get_object_or_404(models.Sales, pk=pk)
    else:
        if not station:
             messages.error(request, "No station associated with your profile.")
             return redirect('wrsm_app:sales')
        sale = get_object_or_404(models.Sales, pk=pk, station=station)
    
    station_settings = models.StationSetting.objects.get(station=sale.station)

    # Use extra=0 for updates to prevent empty forms from appearing/validating
    SalesItemUpdateFormSet = inlineformset_factory(
        models.Sales, 
        models.SalesItem, 
        form=forms.SalesItemForm, 
        extra=0, 
        can_delete=True
    )

    if request.method == 'POST':
        logger.info(f"User {request.user.username} (ID: {request.user.id}) updating Sales ID: {sale.pk}")
        sales_form = forms.CreateSalesForm(request.POST, instance=sale, station=sale.station)
        item_formset = SalesItemUpdateFormSet(request.POST, instance=sale, form_kwargs={'station': sale.station})

        if sales_form.is_valid() and item_formset.is_valid():
            instance = sales_form.save()
            items = item_formset.save(commit=False)
            
            # Handle deleted items
            for deleted_item in item_formset.deleted_objects:
                deleted_item.delete()

            subtotal = 0
            for item in items:
                item.sales = instance
                item.total = item.unit_price * item.quantity
                # Note: Inventory reversal for REFILL/SEAL is complex on update. 
                # For this implementation, we focus on saving the record.
                subtotal += item.total
                item.save()
            
            # Update existing AR record if it exists
            ar_obj = instance.ar_records.first()
            if ar_obj:
                ar_obj.total_amount = subtotal
                ar_obj.customer = instance.customer
                ar_obj.status = "Paid" if instance.is_paid else "Pending"
                ar_obj.save()
                logger.info(f"Updated AR ID: {ar_obj.pk} for Sales ID: {instance.pk}")
            else:
                # Create AR if missing for some reason
                ar_status = "Paid" if instance.is_paid else "Pending"
                models.AccountsReceivable.objects.create(
                    station=instance.station,
                    customer=instance.customer,
                    sales=instance,
                    total_amount=subtotal,
                    status=ar_status
                )
            
            messages.success(request, 'Sales record updated successfully.')
            return HttpResponseRedirect(reverse_lazy('wrsm_app:sales'))
    else:
        sales_form = forms.CreateSalesForm(instance=sale, station=sale.station)
        item_formset = SalesItemUpdateFormSet(instance=sale, form_kwargs={'station': sale.station})
        
    return render(request, 'wrsm/add_sales.html', {
        'form': sales_form,
        'item_formset': item_formset,
        'station': sale.station,
        'station_settings': station_settings,
        'is_update': True
    })


class StationUserListView(LoginRequiredMixin, ListView):
    template_name = 'wrsm/station_users.html'
    model = models.Profile
    context_object_name = 'profiles'

    def get_queryset(self):
        station = self.request.user.profile.station
        return models.Profile.objects.filter(station=station).exclude(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.request.user.profile.station
        return context


class StationUserCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = forms.StationUserCreationForm
    template_name = 'wrsm/station_user_form.html'
    success_message = "User created successfully!"
    success_url = reverse_lazy('wrsm_app:station-users')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['station'] = self.request.user.profile.station
        return kwargs

    def form_valid(self, form):
        station = self.request.user.profile.station
        response = super().form_valid(form)
        models.Profile.objects.create(
            user=self.object,
            station=station,
        )
        models.AuditLog.objects.create(
            station=station,
            action='ADD',
            target_model='User',
            target_object_id=self.object.pk,
            details=f"Added user {self.object.username} with role {form.cleaned_data['role']}",
            performed_by=self.request.user.profile
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.request.user.profile.station
        return context


class StationUserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.User
    form_class = forms.StationUserUpdateForm
    template_name = 'wrsm/station_user_form.html'
    success_message = "User updated successfully!"
    success_url = reverse_lazy('wrsm_app:station-users')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['station'] = self.request.user.profile.station
        return kwargs

    def form_valid(self, form):
        station = self.request.user.profile.station
        response = super().form_valid(form)
        models.AuditLog.objects.create(
            station=station,
            action='EDIT',
            target_model='User',
            target_object_id=self.object.pk,
            details=f"Updated user {self.object.username}",
            performed_by=self.request.user.profile
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.request.user.profile.station
        return context


class StationUserDisableView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.User
    fields = []
    template_name = 'wrsm/station_user_confirm_disable.html'
    success_url = reverse_lazy('wrsm_app:station-users')
    success_message = "User disabled successfully!"

    def form_valid(self, form):
        user = form.instance
        if user == self.request.user:
             messages.error(self.request, "You cannot disable your own account.")
             return redirect('wrsm_app:station-users')
        
        user.is_active = False
        user.save()
        
        station = self.request.user.profile.station
        models.AuditLog.objects.create(
            station=station,
            action='EDIT',
            target_model='User',
            target_object_id=user.pk,
            details=f"Disabled user {user.username}",
            performed_by=self.request.user.profile
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.request.user.profile.station
        return context


class StationUserEnableView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.User
    fields = []
    template_name = 'wrsm/station_user_confirm_enable.html'
    success_url = reverse_lazy('wrsm_app:station-users')
    success_message = "User enabled successfully!"

    def form_valid(self, form):
        user = form.instance
        user.is_active = True
        user.save()
        
        station = self.request.user.profile.station
        models.AuditLog.objects.create(
            station=station,
            action='EDIT',
            target_model='User',
            target_object_id=user.pk,
            details=f"Enabled user {user.username}",
            performed_by=self.request.user.profile
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.request.user.profile.station
        return context


