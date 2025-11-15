from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplica value por arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Resta arg de value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide value por arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0