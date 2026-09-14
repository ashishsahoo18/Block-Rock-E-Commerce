from decimal import Decimal

FREE_SHIPPING_THRESHOLD = Decimal('1000.00')
STANDARD_SHIPPING_FEE = Decimal('99.00')


def calculate_shipping_fee(subtotal: Decimal) -> Decimal:
    """
    Calculates server-side shipping fee.
    Free shipping for orders over or equal to FREE_SHIPPING_THRESHOLD (₹1,000.00).
    Otherwise, standard shipping fee of ₹99.00 applies.
    """
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return STANDARD_SHIPPING_FEE
