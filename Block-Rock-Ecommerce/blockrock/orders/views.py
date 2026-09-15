from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.models import Cart
from products.models import Product

from .forms import CheckoutForm
from .models import Order, OrderItem
from .services import FREE_SHIPPING_THRESHOLD, calculate_shipping_fee


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def checkout(request):
    cart = _get_cart(request.user)
    cart_items = cart.items.select_related('product').filter(product__is_active=True)

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty. Please add products before checking out.')
        return redirect('cart_detail')

    subtotal = sum((item.subtotal for item in cart_items), Decimal('0.00'))
    shipping_fee = calculate_shipping_fee(subtotal)
    total = subtotal + shipping_fee

    initial_data = {
        'shipping_name': request.user.get_full_name() or request.user.username,
        'email': request.user.email,
    }
    form = CheckoutForm(initial=initial_data)

    context = {
        'form': form,
        'cart': cart,
        'items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total': total,
        'free_shipping_threshold': FREE_SHIPPING_THRESHOLD,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
@require_POST
def place_order(request):
    cart = _get_cart(request.user)
    cart_items = cart.items.select_related('product').filter(product__is_active=True)

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty. Please add products before checking out.')
        return redirect('cart_detail')

    form = CheckoutForm(request.POST)

    if not form.is_valid():
        subtotal = sum((item.subtotal for item in cart_items), Decimal('0.00'))
        shipping_fee = calculate_shipping_fee(subtotal)
        total = subtotal + shipping_fee
        messages.error(request, 'Please correct the errors below before placing your order.')
        context = {
            'form': form,
            'cart': cart,
            'items': cart_items,
            'subtotal': subtotal,
            'shipping_fee': shipping_fee,
            'total': total,
            'free_shipping_threshold': FREE_SHIPPING_THRESHOLD,
        }
        return render(request, 'orders/checkout.html', context)

    try:
        with transaction.atomic():
            # Lock cart and products to prevent race conditions & stock over-selling
            locked_cart = Cart.objects.select_for_update().get(user=request.user)
            locked_items = list(locked_cart.items.select_related('product').filter(product__is_active=True))

            if not locked_items:
                raise ValidationError('Your cart is empty.')

            product_ids = [item.product_id for item in locked_items]
            locked_products = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids, is_active=True)
            }

            # Server-side validation of stock and calculations
            items_payload = []
            subtotal = Decimal('0.00')

            for item in locked_items:
                product = locked_products.get(item.product_id)
                if not product:
                    raise ValidationError(f'Product "{item.product.name}" is no longer available.')

                if item.quantity > product.stock:
                    raise ValidationError(
                        f'Insufficient stock for "{product.name}". Only {product.stock} units available.'
                    )

                unit_price = product.current_price
                line_total = unit_price * item.quantity
                subtotal += line_total

                items_payload.append({
                    'product': product,
                    'product_name': product.name,
                    'price': unit_price,
                    'quantity': item.quantity,
                    'line_total': line_total,
                })

            shipping_fee = calculate_shipping_fee(subtotal)
            total = subtotal + shipping_fee

            # Create Order
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = subtotal
            order.shipping_fee = shipping_fee
            order.total = total
            order.status = Order.STATUS_PENDING
            order.save()

            # Create OrderItems & update product stock safely
            order_items = []
            for payload in items_payload:
                order_items.append(
                    OrderItem(
                        order=order,
                        product=payload['product'],
                        product_name=payload['product_name'],
                        price=payload['price'],
                        quantity=payload['quantity'],
                        line_total=payload['line_total'],
                    )
                )
                product = payload['product']
                product.stock -= payload['quantity']
                product.save(update_fields=['stock', 'updated_at'])

            OrderItem.objects.bulk_create(order_items)

            # Clear user cart
            locked_cart.items.all().delete()

        messages.success(request, f'Order #{order.order_number} placed successfully!')
        return redirect('order_confirmation', order_number=order.order_number)

    except ValidationError as e:
        error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
        messages.error(request, error_msg)
        return redirect('checkout')


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user,
    )
    return render(request, 'orders/order_confirmation.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user,
    )
    return render(request, 'orders/order_detail.html', {'order': order})
