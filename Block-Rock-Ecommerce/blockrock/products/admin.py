from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'current_price_display', 'stock', 'is_featured', 'is_deal', 'is_active')
    list_filter = ('category', 'is_featured', 'is_deal', 'is_active')
    search_fields = ('name', 'brand')
    list_select_related = ('category',)
    ordering = ('-created_at',)
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Price', ordering='price')
    def current_price_display(self, product):
        return product.current_price
