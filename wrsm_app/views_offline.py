from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from . import models

@login_required
def get_offline_master_data(request):
    user = request.user
    if not hasattr(user, 'profile') or not user.profile.station:
        return JsonResponse({'error': 'No station assigned'}, status=400)
        
    station = user.profile.station
    
    # 1. Customers & Container Balances
    # Optimize by annotating latest container balance
    latest_inventory = models.ContainerManagement.objects.filter(
        customer=OuterRef('pk')
    ).order_by('-created_date')

    customers = models.Customer.objects.filter(station=station).select_related(
        'promo_code', 'discount_code', 'default_order_type'
    ).annotate(
        latest_balance=Subquery(latest_inventory.values('new_balance')[:1])
    )

    customers_data = {}
    container_balances = {}
    container_history = {}

    for c in customers:
        customers_data[c.id] = {
            'promo_code': c.promo_code.promo_code if c.promo_code else None,
            'promo_description': c.promo_code.promo_description if c.promo_code else None,
            'discount_code': c.discount_code.discount_code if c.discount_code else None,
            'discount_description': c.discount_code.discount_description if c.discount_code else None,
            'discount_rate': c.discount_code.discount_rate if c.discount_code else None,
            'default_order_type': c.default_order_type.pk if c.default_order_type else None,
            'default_ot': c.default_order_type.type if c.default_order_type else None,
            'name': c.name, # Needed for name matching in offline filter
        }
        # default to 0 if no inventory record found
        container_balances[c.id] = c.latest_balance if c.latest_balance is not None else 0

        # Get last 10 records for history
        history_qs = models.ContainerManagement.objects.filter(customer=c).order_by('-created_date')[:10]
        history_list = []
        for h in history_qs:
            history_list.append({
                'pk': h.pk,
                'created_date': h.created_date.strftime('%b. %d, %Y, %I:%M %p').replace('AM', 'a.m.').replace('PM', 'p.m.') if h.created_date else '',
                'timestamp': h.created_date.isoformat() if h.created_date else '',
                'customer': c.name,
                'balance_from_last_visit': h.balance_from_last_visit,
                'delivered_container': h.delivered_container,
                'returned_empty_container': h.returned_empty_container,
                'new_balance': h.new_balance,
                'note': h.note if h.note else '',
                'created_by': str(h.created_by.user) if h.created_by else ''
            })
        container_history[c.id] = history_list

    # 2. Station Settings
    try:
        station_setting = models.StationSetting.objects.get(station=station)
        station_data = {
            'default_order_type_pk': station_setting.default_order_type.pk if station_setting.default_order_type else None,
            'default_order_type_name': station_setting.default_order_type.type if station_setting.default_order_type else None,
        }
    except models.StationSetting.DoesNotExist:
        station_data = {}

    # 3. Order Types
    order_types = models.OrderType.objects.filter(station=station)
    order_types_data = {}
    for ot in order_types:
        order_types_data[ot.id] = {
            'ot_unit_price': ot.unit_price,
            'order_type': ot.type,
        }

    # 4. Products
    products = models.Product.objects.filter(station=station).select_related('jug_size')
    products_data = {}
    for p in products:
        products_data[p.id] = {
            'unit_price': p.unit_price,
            'product_type': p.product_type,
            'jug_size_in_liters': p.jug_size.size_in_liters if p.jug_size else None
        }

    # 5. Jug Sizes
    jug_sizes = models.JugSize.objects.filter(station=station)
    jug_sizes_data = {}
    for js in jug_sizes:
        jug_sizes_data[js.id] = {
            'js_unit_price': js.unit_price
        }

    response_data = {
        'customers': customers_data,
        'container_balances': container_balances,
        'container_history': container_history,
        'station_settings': station_data,
        'order_types': order_types_data,
        'products': products_data,
        'jug_sizes': jug_sizes_data,
    }

    return JsonResponse(response_data)
