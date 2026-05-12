"""Shared logic for safe image URLs in templates and views (Render vs local media)."""
import os

from django.conf import settings


def resolve_hosted_media_url(fieldfile):
    """
    Return image URL only if it should load on the current deployment.

    After DB import, ImageField paths often point to /media/... files that do not
    exist on Render. In production (non-DEBUG), only absolute http(s) URLs
    (e.g. Cloudinary) are returned so callers can fall back to placeholders.
    """
    if not fieldfile:
        return ''
    try:
        url = fieldfile.url
    except ValueError:
        return ''
    if url.startswith(('https://', 'http://', '//')):
        return url
    is_render = os.environ.get('RENDER', '').lower() in ('1', 'true', 'yes')
    if is_render:
        return ''
    if getattr(settings, 'DEBUG', False):
        return url
    return ''
