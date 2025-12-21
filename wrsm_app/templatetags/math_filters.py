from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    return value * arg

@register.filter(name='subtract')
def subtract(value, arg):
    return float(value) - float(arg)

@register.filter(name='divide')
def divide(value, arg):
    return value / arg

@register.filter(name='add')
def add(value, arg):
    return value + arg

@register.filter(name='integer')
def integer(value):
    return int(value)