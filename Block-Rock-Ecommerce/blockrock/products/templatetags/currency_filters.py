from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter(name='rupee')
def rupee_format(value):
    """
    Formats a numeric value using Indian currency format (e.g., ₹64,999 or ₹1,29,999).
    """
    if value is None or value == '':
        return ''
    try:
        dec = Decimal(str(value))
        val_int = int(dec)
        s = str(val_int)
        if len(s) <= 3:
            formatted = s
        else:
            last_three = s[-3:]
            remaining = s[:-3]
            groups = []
            while len(remaining) > 2:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.append(remaining)
            groups.reverse()
            formatted = ','.join(groups) + ',' + last_three
        return f'₹{formatted}'
    except (ValueError, TypeError, InvalidOperation):
        return f'₹{value}'
