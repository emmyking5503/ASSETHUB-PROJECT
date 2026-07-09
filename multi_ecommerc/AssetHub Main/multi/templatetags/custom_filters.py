from django import template

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """Get a value from a dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key in templates"""
    if dictionary is None:
        return None
    return dictionary.get(key)

