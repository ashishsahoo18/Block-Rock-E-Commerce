from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductVariant, Banner, SizeChart


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('thumbnail_preview', 'image', 'sort_order', 'is_primary', 'alt_text')
    readonly_fields = ('thumbnail_preview',)

    @admin.display(description='Preview')
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #444;" />',
                obj.image.url
            )
        return "No image"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color_name', 'color_hex', 'color_preview', 'stock', 'price_override', 'sku', 'is_active')
    readonly_fields = ('color_preview',)

    @admin.display(description='Swatch')
    def color_preview(self, obj):
        if obj.color_hex:
            return format_html(
                '<span style="display:inline-block; width: 24px; height: 24px; border-radius: 50%; background-color: {}; border: 1px solid #666; vertical-align: middle;"></span>',
                obj.color_hex
            )
        return "—"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_ingot_original', 'is_active', 'created_at')
    list_filter = ('is_ingot_original', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'brand', 'category', 'current_price_display', 'compare_at_price',
        'stock', 'is_featured', 'is_deal', 'is_ingot_original', 'is_active'
    )
    list_filter = ('is_ingot_original', 'category', 'is_featured', 'is_deal', 'is_active')
    search_fields = ('name', 'brand', 'description')
    list_select_related = ('category',)
    list_editable = ('is_featured', 'is_deal', 'is_active')
    ordering = ('-created_at',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand', 'category', 'short_description', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'discount_price', 'compare_at_price', 'discount', 'stock')
        }),
        ('Default Main Image', {
            'fields': ('image',),
            'description': 'Main fallback image. Additional images with ordering & thumbnails should be added via the Product Images inline below.'
        }),
        ('Storefront Flags & Collection', {
            'fields': ('is_active', 'is_featured', 'is_deal', 'is_ingot_original')
        }),
        ('Ratings (System)', {
            'classes': ('collapse',),
            'fields': ('rating', 'review_count')
        }),
    )

    @admin.display(description='Selling Price', ordering='price')
    def current_price_display(self, product):
        return product.current_price


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'tagline', 'button_text', 'link_url', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle', 'tagline')
    list_editable = ('sort_order', 'is_active')
    ordering = ('sort_order', '-created_at')


@admin.register(SizeChart)
class SizeChartAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'description')
    ordering = ('name',)

