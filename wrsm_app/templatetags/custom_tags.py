from django import template

from wrsm_app.media_utils import resolve_hosted_media_url

register = template.Library()


@register.filter
def hosted_media_url(fieldfile):
    """
    Return image URL only if it will load on the current deployment.

    After DB import, ImageField paths often point to /media/... files that do not
    exist on Render. In production (DEBUG=False), only absolute http(s) URLs
    (e.g. Cloudinary) are returned so templates can fall back to placeholders.
    """
    return resolve_hosted_media_url(fieldfile)

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