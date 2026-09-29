from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_ingot_original = models.BooleanField(
        default=False,
        help_text="Designates whether this category belongs to the INGOT Originals collection."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=220, blank=True)
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Compare-at / MRP price for strikethrough & 'you save' calculation"
    )
    # Kept so existing records and the original project data remain compatible.
    discount = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_deal = models.BooleanField(default=False)
    is_ingot_original = models.BooleanField(
        default=False,
        verbose_name="INGOT Original",
        help_text="Designates whether this product belongs to the INGOT Originals collection."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'name']

    def clean(self):
        if self.discount_price is not None and self.discount_price > self.price:
            raise ValidationError({'discount_price': 'Discount price cannot be greater than the regular price.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'product'
            slug = base_slug
            suffix = 2
            while Product.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        return self.discount_price if self.discount_price is not None else self.price

    @property
    def mrp(self):
        """Returns the MRP/Compare-at price if present and greater than current price."""
        if self.compare_at_price and self.compare_at_price > self.current_price:
            return self.compare_at_price
        if self.discount_price is not None and self.price > self.discount_price:
            return self.price
        return None

    @property
    def you_save_amount(self):
        if self.mrp and self.mrp > self.current_price:
            return self.mrp - self.current_price
        return Decimal('0.00')

    @property
    def discount_percentage(self):
        if self.mrp and self.mrp > self.current_price:
            return int(((self.mrp - self.current_price) / self.mrp) * 100)
        if self.discount_price is not None and self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return self.discount

    @property
    def in_stock(self):
        if self.variants.filter(is_active=True).exists():
            return any(v.stock > 0 for v in self.variants.filter(is_active=True))
        return self.stock > 0

    @property
    def primary_image_url(self):
        primary = self.images.filter(is_primary=True).first() or self.images.order_by('sort_order', 'id').first()
        if primary and primary.image:
            return primary.image.url
        if self.image:
            return self.image.url
        return ''

    @property
    def secondary_image_url(self):
        imgs = list(self.images.order_by('sort_order', 'id'))
        if len(imgs) > 1 and imgs[1].image:
            return imgs[1].image.url
        return ''

    @property
    def has_variants(self):
        return self.variants.filter(is_active=True).exists()

    @property
    def active_variants(self):
        return self.variants.filter(is_active=True).order_by('sort_order' if hasattr(ProductVariant, 'sort_order') else 'id')

    @property
    def available_sizes(self):
        sizes = []
        for s in self.variants.filter(is_active=True).values_list('size', flat=True).distinct():
            if s and s not in sizes:
                sizes.append(s)
        return sizes

    @property
    def available_colors(self):
        colors = []
        seen = set()
        for v in self.variants.filter(is_active=True):
            if v.color_name and v.color_name not in seen:
                seen.add(v.color_name)
                colors.append({
                    'name': v.color_name,
                    'hex': v.color_hex or '#000000',
                })
        return colors

    @property
    def collection_name(self):
        return "INGOT Originals" if self.is_ingot_original else "Electronics"

    @property
    def is_original(self):
        return self.is_ingot_original or (self.category and getattr(self.category, 'is_ingot_original', False))

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order (lowest first)")
    is_primary = models.BooleanField(default=False, help_text="Set as primary thumbnail / hero image")
    alt_text = models.CharField(max_length=255, help_text="Required descriptive alt text for accessibility")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'product image'
        verbose_name_plural = 'product images'

    def clean(self):
        if not self.alt_text:
            raise ValidationError({'alt_text': 'Alt text is required for accessibility.'})

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary image per product
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} Image #{self.pk}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=32, blank=True, help_text="e.g. S, M, L, XL, XXL, or Free Size")
    color_name = models.CharField(max_length=64, blank=True, help_text="e.g. Stealth Black, Cyan Accent, Heather Grey")
    color_hex = models.CharField(max_length=16, blank=True, default='#111111', help_text="Hex code e.g. #00F0FF for color swatch rendering")
    stock = models.PositiveIntegerField(default=0, help_text="Available inventory for this variant")
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Optional custom price for this variant. If left blank, base product price is used."
    )
    sku = models.CharField(max_length=64, blank=True, help_text="Optional unique SKU identifier")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['size', 'color_name', 'id']
        verbose_name = 'product variant'
        verbose_name_plural = 'product variants'

    @property
    def display_name(self):
        parts = []
        if self.size:
            parts.append(f"Size: {self.size}")
        if self.color_name:
            parts.append(f"Color: {self.color_name}")
        return " / ".join(parts) or "Default"

    @property
    def current_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.current_price

    @property
    def in_stock(self):
        return self.stock > 0

    def __str__(self):
        return f"{self.product.name} ({self.display_name}) - Stock: {self.stock}"


class Banner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    tagline = models.CharField(max_length=100, blank=True, help_text="Eyebrow badge text e.g. NEXT-GEN APPAREL")
    link_url = models.CharField(max_length=255, default='/shop/', help_text="Destination URL for CTA")
    button_text = models.CharField(max_length=50, default='Shop Collection')
    image = models.ImageField(upload_to='banners/', blank=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Slide display order (lowest first)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = 'hero banner'
        verbose_name_plural = 'hero banners'

    def __str__(self):
        return self.title


class SizeChart(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='size_charts')
    description = models.TextField(blank=True)
    chart_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured JSON table with headers, cm measurements, and inch measurements"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'size chart'
        verbose_name_plural = 'size charts'

    def __str__(self):
        return self.name

