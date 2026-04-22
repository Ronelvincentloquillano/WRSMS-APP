from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except (TypeError, AttributeError):
        return None

@register.filter
def remove_none(value):
    if value is None:
        return ''
    return value

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter
def integer(value):
    return int(value)