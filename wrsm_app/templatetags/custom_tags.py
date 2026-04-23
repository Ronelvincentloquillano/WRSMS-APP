from django import template
from django.conf import settings
import os

register = template.Library()


@register.filter
def hosted_media_url(fieldfile):
    """
    Return image URL only if it will load on the current deployment.

    After DB import, ImageField paths often point to /media/... files that do not
    exist on Render. In production (DEBUG=False), only absolute http(s) URLs
    (e.g. Cloudinary) are returned so templates can fall back to placeholders.
    """
    if not fieldfile:
        return ''
    try:
        url = fieldfile.url
    except ValueError:
        return ''
    if (
        url.startswith('https://')
        or url.startswith('http://')
        or url.startswith('//')
    ):
        return url
    # On Render, old DB paths usually point to missing /media files.
    # Force template fallback instead of returning broken local paths.
    is_render = os.environ.get('RENDER', '').lower() in ('1', 'true', 'yes')
    if is_render:
        return ''
    if getattr(settings, 'DEBUG', False):
        return url
    return ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

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