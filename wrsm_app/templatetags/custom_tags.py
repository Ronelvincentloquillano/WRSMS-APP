from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def remove_none(value):
    if value is None:
        return ''
    return value

@register.filter
def integer(value):
    return int(value)