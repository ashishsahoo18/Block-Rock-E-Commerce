from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'variant_label', 'product_name', 'price', 'quantity', 'line_total')
    readonly_fields = ('product', 'variant_label', 'product_name', 'price', 'quantity', 'line_total')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'shipping_name', 'total', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('order_number', 'shipping_name', 'email', 'phone', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'user', 'subtotal', 'shipping_fee', 'total', 'created_at', 'updated_at')
    list_editable = ('status',)
    inlines = [OrderItemInline]
    ordering = ('-created_at',)
    fieldsets = (
        ('Order Header', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Shipping Details', {
            'fields': ('shipping_name', 'email', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Payment & Totals', {
            'fields': ('payment_method', 'subtotal', 'shipping_fee', 'total')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'variant_label', 'price', 'quantity', 'line_total')
    search_fields = ('order__order_number', 'product_name', 'variant_label')
    readonly_fields = ('order', 'product', 'variant', 'variant_label', 'product_name', 'price', 'quantity', 'line_total')
