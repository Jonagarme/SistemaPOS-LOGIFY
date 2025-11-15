import base64
from django import template

register = template.Library()

@register.filter
def base64_encode(value):
    """Convierte bytes a base64 para mostrar en templates"""
    if value:
        try:
            return base64.b64encode(value).decode('utf-8')
        except:
            return ''
    return ''