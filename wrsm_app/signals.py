from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from . import models

# Product names (substring match, case-insensitive) whose on-hand Product.quantity
# decreases when sold. Excludes refills, jugs, and delivery charges by type.
STOCK_TRACKED_SEAL_NAME_FRAGMENTS = (
    'umbrella seal',
    'faucet seal',
    'bigcap seal',
    'big cap seal',
    'small cap seal',
    'round cap seal',
    'transparent seal',
    'transparent plastic',
)


def _normalize_product_name(name):
    if not name:
        return ''
    return ' '.join(str(name).lower().split())


def is_stock_tracked_seal_product(product):
    if not product or not getattr(product, 'pk', None):
        return False
    ptype = (product.product_type or '').strip().upper()
    if ptype in ('REFILL', 'JUG', 'DELIVERY CHARGE'):
        return False
    name = _normalize_product_name(product.product_name)
    if not name:
        return False
    return any(fragment in name for fragment in STOCK_TRACKED_SEAL_NAME_FRAGMENTS)


def apply_named_seal_stock_delta(product_id, delta):
    """delta > 0 adds to stock; delta < 0 removes (customer purchase)."""
    if not product_id or delta == 0:
        return
    product = models.Product.objects.filter(pk=product_id).only(
        'id', 'product_name', 'product_type'
    ).first()
    if not product or not is_stock_tracked_seal_product(product):
        return
    models.Product.objects.filter(pk=product_id).update(
        quantity=Coalesce(F('quantity'), Value(0)) + Value(delta)
    )


@receiver(pre_save, sender=models.Product)
def product_cache_unit_price_before_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.only('unit_price').get(pk=instance.pk).unit_price
        except sender.DoesNotExist:
            old = None
    else:
        old = None
    instance._unit_price_before_save = old


@receiver(post_save, sender=models.Product)
def product_log_unit_price_change(sender, instance, created, **kwargs):
    old_price = getattr(instance, '_unit_price_before_save', None)
    new_price = instance.unit_price
    if old_price == new_price:
        return
    if old_price is None and new_price is None:
        return

    changed_by = instance.modified_by if not created else instance.created_by
    models.ProductPriceHistory.objects.create(
        product=instance,
        station=instance.station,
        previous_price=old_price,
        new_price=new_price,
        changed_by=changed_by,
    )


@receiver(pre_save, sender=models.SalesItem)
def sales_item_stock_pre_save(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    if instance.pk:
        try:
            old = sender.objects.only('product_id', 'quantity').get(pk=instance.pk)
            instance._stock_prev_product_id = old.product_id
            instance._stock_prev_quantity = int(old.quantity)
        except sender.DoesNotExist:
            instance._stock_prev_product_id = None
            instance._stock_prev_quantity = 0
    else:
        instance._stock_prev_product_id = None
        instance._stock_prev_quantity = 0


@receiver(post_save, sender=models.SalesItem)
def sales_item_stock_post_save(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if not instance.product_id:
        return

    prev_pid = getattr(instance, '_stock_prev_product_id', None)
    prev_qty = getattr(instance, '_stock_prev_quantity', 0) or 0
    new_pid = instance.product_id
    new_qty = int(instance.quantity)

    if created:
        apply_named_seal_stock_delta(new_pid, -new_qty)
        return

    if prev_pid == new_pid:
        apply_named_seal_stock_delta(new_pid, prev_qty - new_qty)
    else:
        if prev_pid:
            apply_named_seal_stock_delta(prev_pid, prev_qty)
        apply_named_seal_stock_delta(new_pid, -new_qty)


@receiver(post_delete, sender=models.SalesItem)
def sales_item_stock_post_delete(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    if not instance.product_id:
        return
    qty = int(instance.quantity)
    apply_named_seal_stock_delta(instance.product_id, qty)
