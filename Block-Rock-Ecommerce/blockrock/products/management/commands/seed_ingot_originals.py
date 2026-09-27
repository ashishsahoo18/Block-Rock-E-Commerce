import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from products.models import Category, Product


ORIGINALS_CATEGORIES = [
    ('T-Shirts', 'INGOT signature streetwear and premium organic cotton tees.'),
    ('Hoodies', 'Heavyweight French terry and fleece hoodies with minimalist INGOT branding.'),
    ('Sweatshirts', 'Classic crewneck sweatshirts designed for comfort and durability.'),
    ('Caps', 'Structured and performance caps featuring embroidered INGOT wordmark.'),
    ('Bags', 'Weather-resistant urban backpacks, sleek sling bags, and daily totes.'),
    ('Lifestyle', 'Desk mats, insulated bottles, and daily essentials crafted for the modern workspace.'),
]

# (Name, Category, Price, Stock, is_featured, is_deal, Description, ShortDesc, MRP/RegularPrice, ImageFile)
ORIGINALS_PRODUCTS = [
    # 1-7: T-Shirts
    (
        "INGOT Essential T-Shirt", "T-Shirts", "999.00", 45, True, True,
        "Crafted from 100% combed organic cotton (220 GSM) with a relaxed modern drape and micro-silicone INGOT chest branding.",
        "220 GSM Organic Cotton, Relaxed fit, Micro-silicone chest logo.",
        "1299.00", "products/originals/ingot-essential-t-shirt.png"
    ),
    (
        "INGOT Signature T-Shirt", "T-Shirts", "1299.00", 35, True, False,
        "Minimalist heavyweight tee with high-density embroidered cyan INGOT wordmark on the chest. Pre-shrunk for enduring structure.",
        "240 GSM Heavyweight cotton, 3D embroidered cyan logo, Ribbed collar.",
        None, "products/originals/ingot-signature-t-shirt.png"
    ),
    (
        "INGOT Premium T-Shirt", "T-Shirts", "1499.00", 30, False, True,
        "Ultra-soft Peruvian Pima cotton tee engineered with taped shoulder seams and a tailored athletic cut.",
        "100% Pima Cotton, Silk-soft touch, Reinforced shoulder seams.",
        "1799.00", "products/originals/ingot-premium-t-shirt.png"
    ),
    (
        "INGOT Oversized T-Shirt", "T-Shirts", "1399.00", 40, True, False,
        "Drop-shoulder boxy silhouette inspired by Japanese streetwear. Heavy drape that holds its shape wash after wash.",
        "Boxy streetwear cut, 260 GSM French terry cotton, Dropped shoulders.",
        None, "products/originals/ingot-oversized-t-shirt.png"
    ),
    (
        "INGOT Tech T-Shirt", "T-Shirts", "1199.00", 35, False, True,
        "Breathable moisture-wicking four-way stretch fabric designed for high-performance mobility, commuting, and workouts.",
        "Dry-fit poly-spandex blend, 4-way stretch, Anti-odor treatment.",
        "1499.00", "products/originals/ingot-tech-t-shirt.png"
    ),
    (
        "INGOT Graphic T-Shirt", "T-Shirts", "1299.00", 28, False, False,
        "Contemporary digital art print with neon cyan geometric motif on pitch-black cotton. Screen printed with water-based eco inks.",
        "Custom geometric screen print, 200 GSM ring-spun cotton, Eco inks.",
        None, "products/originals/ingot-graphic-t-shirt.png"
    ),
    (
        "INGOT Everyday T-Shirt", "T-Shirts", "899.00", 50, False, False,
        "Your daily go-to wardrobe essential. Super-soft ring-spun cotton with ribbed crew collar and tagless comfort label.",
        "180 GSM Ring-spun cotton, Tagless comfort, Pre-washed finish.",
        None, "products/originals/ingot-everyday-t-shirt.png"
    ),

    # 8-11: Hoodies
    (
        "INGOT Premium Hoodie", "Hoodies", "2999.00", 25, True, True,
        "400 GSM heavyweight brushed fleece hoodie with double-layer hood, brushed chrome metal aglets, and embossed cyan chest logo.",
        "400 GSM Brushed Fleece, Chrome aglets, Double-lined structured hood.",
        "3799.00", "products/originals/ingot-premium-hoodie.png"
    ),
    (
        "INGOT Essential Hoodie", "Hoodies", "2499.00", 30, True, False,
        "Cozy mid-weight fleece pullover featuring a seamless kangaroo pocket and clean minimalist chest emblem.",
        "320 GSM Midweight fleece, Kangaroo pocket, Ribbed cuffs & hem.",
        None, "products/originals/ingot-essential-hoodie.png"
    ),
    (
        "INGOT Oversized Hoodie", "Hoodies", "2799.00", 20, False, True,
        "Contemporary relaxed streetwear drape with dropped shoulders, elongated ribbed cuffs, and high-density cyan branding.",
        "Streetwear boxy fit, 380 GSM loopback terry, Extended cuffs.",
        "3299.00", "products/originals/ingot-oversized-hoodie.png"
    ),
    (
        "INGOT Zip Hoodie", "Hoodies", "2899.00", 22, False, False,
        "Full-zip hooded jacket featuring matte black dual YKK zippers, hidden headphone cable pass-through, and thermal fleece lining.",
        "Matte black YKK dual zipper, Hidden media port, Thermal fleece.",
        None, "products/originals/ingot-zip-hoodie.png"
    ),

    # 12: Sweatshirts
    (
        "INGOT Premium Sweatshirt", "Sweatshirts", "2299.00", 26, True, True,
        "Classic crewneck sweatshirt with triangular rib insert at neck, cover-stitched seams, and micro-embroidered INGOT chest icon.",
        "350 GSM Loopback cotton, V-stitch collar detail, Flatlock seams.",
        "2699.00", "products/originals/ingot-premium-sweatshirt.png"
    ),

    # 13-14: Caps
    (
        "INGOT Signature Cap", "Caps", "899.00", 40, True, True,
        "6-panel structured baseball cap with 3D embroidered cyan INGOT wordmark, curved visor with cyan sandwich accent, and brass buckle strap.",
        "Structured 6-panel twill, 3D embroidery, Antique brass buckle strap.",
        "1099.00", "products/originals/ingot-signature-cap.png"
    ),
    (
        "INGOT Premium Cap", "Caps", "1099.00", 30, False, False,
        "Water-resistant performance ripstop cap with magnetic FIDLOCK closure, laser-perforated side breathability, and reflective rear tab.",
        "DWR treated ripstop, FIDLOCK magnetic strap, Laser cut vents.",
        None, "products/originals/ingot-premium-cap.png"
    ),

    # 15-18: Bags
    (
        "INGOT Everyday Backpack", "Bags", "2499.00", 25, True, True,
        "24L weather-resistant cordura pack with dedicated 16-inch padded laptop sleeve, water bottle pocket, and luggage pass-through strap.",
        "24L Cordura ballistic nylon, Padded 16\" laptop bay, Luggage strap.",
        "2999.00", "products/originals/ingot-everyday-backpack.png"
    ),
    (
        "INGOT Premium Backpack", "Bags", "3499.00", 18, True, True,
        "30L commuter travel pack with water-resistant YKK Aquaguard zips, ergonomic airmesh back panel, and magnetic quick-access pockets.",
        "30L Waterproof Cordura, YKK Aquaguard zips, Ergonomic airmesh.",
        "4199.00", "products/originals/ingot-premium-backpack.png"
    ),
    (
        "INGOT Sling Bag", "Bags", "1699.00", 32, True, False,
        "Compact cross-body sling bag with fidlock magnetic buckle, waterproof fabric, padded iPad mini sleeve, and hidden passport security pocket.",
        "Weatherproof sailcloth, Magnetic FIDLOCK buckle, iPad mini sleeve.",
        None, "products/originals/ingot-sling-bag.png"
    ),
    (
        "INGOT Tote Bag", "Bags", "999.00", 45, False, True,
        "Heavy-duty 16oz cotton canvas tote with reinforced box-stitched handles, secure top zip closure, and interior organizing compartments.",
        "16oz Heavy canvas, Top zip security, Dual reinforced carry handles.",
        "1199.00", "products/originals/ingot-tote-bag.png"
    ),

    # 19-20: Lifestyle
    (
        "INGOT Desk Mat", "Lifestyle", "1299.00", 50, True, True,
        "900x400mm premium vegan leather desk mat with anti-fray precision stitching, water-resistant surface, and non-slip suede base.",
        "900x400mm Vegan Leather, Anti-fray stitching, Non-slip suede base.",
        "1599.00", "products/originals/ingot-desk-mat.png"
    ),
    (
        "INGOT Water Bottle", "Lifestyle", "1199.00", 40, False, False,
        "750ml vacuum-insulated double-wall stainless steel bottle. Keeps drinks cold 24h / hot 12h with leakproof insulated carry cap.",
        "750ml 18/8 Pro stainless steel, TempShield vacuum insulated, Leakproof.",
        None, "products/originals/ingot-water-bottle.png"
    ),
]


class Command(BaseCommand):
    help = 'Seed exactly 20 active INGOT Originals products into the database.'

    def handle(self, *args, **options):
        category_map = {}
        for name, description in ORIGINALS_CATEGORIES:
            category, created = Category.objects.update_or_create(
                name=name,
                defaults={
                    'description': description,
                    'is_active': True,
                    'is_ingot_original': True,
                },
            )
            category_map[name] = category

        seeded_names = set()

        for item in ORIGINALS_PRODUCTS:
            (name, cat_name, price_str, stock, is_featured, is_deal,
             description, short_desc, mrp_str, image_path) = item

            target_price = Decimal(price_str)
            if is_deal and mrp_str:
                mrp = Decimal(mrp_str)
                sale_price = target_price
                regular_price = mrp
            else:
                regular_price = target_price
                sale_price = None

            legacy_discount = (
                int(((regular_price - sale_price) / regular_price) * 100)
                if sale_price and regular_price else 0
            )

            product, created = Product.objects.update_or_create(
                name=name,
                defaults={
                    'brand': 'INGOT',
                    'category': category_map[cat_name],
                    'description': description,
                    'short_description': short_desc,
                    'price': regular_price,
                    'discount_price': sale_price,
                    'discount': legacy_discount,
                    'stock': stock,
                    'rating': 0.0,
                    'review_count': 0,
                    'is_featured': is_featured,
                    'is_deal': is_deal,
                    'is_ingot_original': True,
                    'is_active': True,
                    'image': image_path,
                },
            )
            seeded_names.add(name)

        active_originals = Product.objects.filter(is_active=True, is_ingot_original=True).count()
        active_electronics = Product.objects.filter(is_active=True, is_ingot_original=False).count()
        total_active = Product.objects.filter(is_active=True).count()
        total_db = Product.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {len(category_map)} INGOT Originals categories and {len(seeded_names)} products.\n'
            f'Active Electronics: {active_electronics} | Active Originals: {active_originals} | Total Active: {total_active} | Total in DB: {total_db}'
        ))
