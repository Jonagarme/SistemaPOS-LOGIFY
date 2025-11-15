from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filtro personalizado para obtener un elemento de un diccionario usando una clave dinámica.
    Útil cuando necesitas acceder a elementos de diccionario en templates con claves variables.
    
    Uso en template:
    {{ my_dict|get_item:variable_key }}
    
    Equivale a:
    my_dict[variable_key] en Python
    """
    if dictionary is None:
        return None
    
    # Si es un diccionario, intentar obtener el valor
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    
    # Si es una lista o tuple, intentar obtener por índice
    if hasattr(dictionary, '__getitem__'):
        try:
            return dictionary[key]
        except (KeyError, IndexError, TypeError):
            return None
    
    return None

@register.filter
def get_attr(obj, attr_name):
    """
    Filtro para obtener un atributo de un objeto usando un nombre dinámico.
    
    Uso en template:
    {{ my_object|get_attr:variable_attr_name }}
    
    Equivale a:
    getattr(my_object, variable_attr_name) en Python
    """
    if obj is None:
        return None
    
    try:
        return getattr(obj, attr_name, None)
    except (AttributeError, TypeError):
        return None

@register.filter
def multiply(value, arg):
    """
    Filtro para multiplicar dos valores.
    
    Uso en template:
    {{ number|multiply:factor }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Filtro para dividir dos valores.
    
    Uso en template:
    {{ number|divide:divisor }}
    """
    try:
        divisor = float(arg)
        if divisor == 0:
            return 0
        return float(value) / divisor
    except (ValueError, TypeError):
        return 0