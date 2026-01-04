from django import template
from django.template.defaultfilters import stringfilter
import markdown as md
import re

register = template.Library()

@register.filter()
@stringfilter
def markdown(value):
    # Pre-process to ensure blank line before lists (helps non-technical users)
    # Matches a line that doesn't start with a bullet/space, followed by a bullet line
    value = re.sub(r'^([^ \t\*\-\+\n].*)\n(\s*[\*\-\+]\s)', r'\1\n\n\2', value, flags=re.MULTILINE)
    
    return md.markdown(value, extensions=[
        'markdown.extensions.fenced_code', 
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists'
    ])
