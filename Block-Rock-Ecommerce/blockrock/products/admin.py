from django.contrib import admin
from django.contrib import messages
from django.db.models import Q
from django.utils.html import format_html
from django.utils import timezone
from accounts.services import queue_product_campaign
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


class ProductAvailabilityFilter(admin.SimpleListFilter):
    title = 'availability'
    parameter_name = 'availability'

    def lookups(self, request, model_admin):
        return (('in_stock', 'In stock'), ('out_of_stock', 'Out of stock'))

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(
                Q(stock__gt=0) | Q(variants__stock__gt=0, variants__is_active=True)
            ).distinct()
        if self.value() == 'out_of_stock':
            return queryset.filter(stock=0).exclude(
                variants__stock__gt=0, variants__is_active=True
            ).distinct()
        return queryset


class ProductPriceRangeFilter(admin.SimpleListFilter):
    title = 'selling price'
    parameter_name = 'price_range'

    def lookups(self, request, model_admin):
        return (
            ('under_75000', 'Under ₹75,000'),
            ('75000_125000', '₹75,000–₹1,25,000'),
            ('125000_200000', '₹1,25,000–₹2,00,000'),
            ('over_200000', 'Over ₹2,00,000'),
        )

    def queryset(self, request, queryset):
        ranges = {
            'under_75000': {'discount_price__lt': 75000},
            '75000_125000': {'discount_price__gte': 75000, 'discount_price__lt': 125000},
            '125000_200000': {'discount_price__gte': 125000, 'discount_price__lt': 200000},
            'over_200000': {'discount_price__gte': 200000},
        }
        params = ranges.get(self.value())
        return queryset.filter(**params) if params else queryset


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
    list_filter = (
        'brand', 'category', ProductPriceRangeFilter, ProductAvailabilityFilter,
        'is_ingot_original', 'is_featured', 'is_deal', 'is_active',
    )
    search_fields = ('name', 'slug', 'brand', 'description')
    list_select_related = ('category',)
    list_editable = ('is_featured', 'is_deal', 'is_active')
    ordering = ('-created_at',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ('queue_product_newsletter_announcements',)
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.is_active:
            _, created = queue_product_campaign(obj)
            if created:
                self.message_user(
                    request,
                    'New-product newsletter notification queued for delivery.',
                    level=messages.INFO,
                )

    @admin.action(description='Queue selected active products for a newsletter announcement')
    def queue_product_newsletter_announcements(self, request, queryset):
        queued = 0
        skipped = 0
        for product in queryset:
            _, created = queue_product_campaign(product)
            if created:
                queued += 1
            else:
                skipped += 1
        if queued:
            self.message_user(
                request,
                f'{queued} product announcement(s) queued for delivery.',
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f'{skipped} product(s) were inactive or had already been queued.',
                level=messages.INFO,
            )

    def _has_protected_references(self, product):
        return (
            product.cart_items.exists()
            or product.wishlist_items.exists()
            or product.order_items.exists()
        )

    def _archive_product(self, request, product):
        product.is_active = False
        product.is_featured = False
        product.is_deal = False
        product.updated_at = timezone.now()
        product.save(update_fields=('is_active', 'is_featured', 'is_deal', 'updated_at'))
        self.message_user(
            request,
            f'{product.name} was archived instead of deleted because it is referenced by customer or order data.',
            level=messages.WARNING,
        )

    def delete_model(self, request, product):
        if self._has_protected_references(product):
            self._archive_product(request, product)
            return
        super().delete_model(request, product)

    def delete_queryset(self, request, queryset):
        protected_products = []
        deletable_ids = []
        for product in queryset:
            if self._has_protected_references(product):
                protected_products.append(product.pk)
            else:
                deletable_ids.append(product.pk)

        if protected_products:
            Product.objects.filter(pk__in=protected_products).update(
                is_active=False,
                is_featured=False,
                is_deal=False,
                updated_at=timezone.now(),
            )
            self.message_user(
                request,
                f'{len(protected_products)} referenced product(s) were archived instead of deleted.',
                level=messages.WARNING,
            )
        if deletable_ids:
            Product.objects.filter(pk__in=deletable_ids).delete()


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
