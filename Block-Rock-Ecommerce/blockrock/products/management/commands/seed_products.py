from decimal import Decimal
from django.core.management.base import BaseCommand
from products.models import Category, Product


CATEGORIES = [
    ('Smartphones', 'Flagship smartphones, everyday essentials, and mobile accessories.'),
    ('Laptops', 'Portable power for work, study, and creative projects.'),
    ('Audio', 'Headphones, wireless earbuds, speakers, and sound systems.'),
    ('Wearables', 'Smartwatches, fitness bands, and wrist companions.'),
    ('Computer Accessories', 'Keyboards, mice, hubs, stands, and external storage.'),
    ('Gaming', 'Controllers, chairs, RGB gear, and gaming peripherals.'),
    ('Cameras', '4K vision cams, action cams, and compact creator cameras.'),
    ('Accessories', 'Fast chargers, power banks, cables, and smart home hubs.'),
]

# Product Tuples:
# (Name, Category, Price, Stock, Featured, Deal, Rating, ReviewCount, Description, ShortDesc, MRP/RegularPrice)
# If Deal=True, MRP is set higher so discount_price = Price (the deal price) and price = MRP.
PRODUCTS = [
    # 1-4: Laptops
    ("Block Rock ProBook 14", "Laptops", "64999.00", 12, True, False, 4.7, 142, "Powerful 14-inch professional laptop with vibrant display and all-day battery life.", "14-inch IPS, Intel Core i7, 16GB RAM, 512GB SSD.", None),
    ("Block Rock UltraBook 15", "Laptops", "72499.00", 8, True, False, 4.8, 98, "Ultra-thin 15-inch magnesium laptop designed for creators on the move.", "15.6-inch OLED, Ryzen 7, 16GB RAM, 1TB SSD.", None),
    ("Block Rock Gaming Laptop X1", "Laptops", "89999.00", 6, True, True, 4.9, 210, "High-performance gaming machine with high-refresh display and dedicated GPU.", "16-inch 165Hz, RTX 4060, 16GB DDR5, 1TB NVMe.", "104999.00"),
    ("Block Rock AirBook 13", "Laptops", "54999.00", 15, False, True, 4.5, 76, "Lightweight 13-inch companion ideal for study, writing, and everyday browsing.", "13.3-inch Retina, Quad-Core, 8GB RAM, 256GB SSD.", "62999.00"),

    # 5-8: Smartphones
    ("Block Rock Nova X5", "Smartphones", "34999.00", 20, True, False, 4.6, 185, "Sleek 5G smartphone with 108MP camera and fast 67W charging.", "6.67-inch AMOLED 120Hz, 8GB RAM, 256GB storage.", None),
    ("Block Rock Pixel Pro", "Smartphones", "49999.00", 10, True, True, 4.8, 320, "Flagship AI smartphone with advanced computational photography tools.", "6.7-inch Quad HD+ LTPO, 12GB RAM, 256GB storage.", "56999.00"),
    ("Block Rock Edge 5G", "Smartphones", "27999.00", 25, False, True, 4.4, 154, "Curved display 5G phone offering smooth performance and stylish design.", "6.55-inch Curved OLED, 8GB RAM, 128GB storage.", "31999.00"),
    ("Block Rock Lite 5G", "Smartphones", "19999.00", 30, False, False, 4.3, 112, "Accessible 5G connectivity with long-lasting 5000mAh battery.", "6.5-inch FHD+, 6GB RAM, 128GB storage.", None),

    # 9-12: Audio
    ("Block Rock AirPods Pro X", "Audio", "7999.00", 35, True, True, 4.8, 410, "True wireless earbuds with active noise cancellation and spatial sound.", "Active Noise Cancellation, 30h battery with case, IPX4.", "9999.00"),
    ("Block Rock Studio Headphones", "Audio", "5499.00", 18, True, False, 4.7, 165, "Over-ear studio monitor headphones delivering precise, balanced audio.", "40mm Drivers, Memory foam earcups, Detachable cable.", None),
    ("Block Rock Bass Buds", "Audio", "2499.00", 45, False, True, 4.4, 280, "Punchy deep-bass wireless earphones built for workouts and daily commute.", "10mm Dynamic Drivers, 24h total playback, Fast charge.", "3199.00"),
    ("Block Rock Mini Speaker", "Audio", "1999.00", 40, False, False, 4.5, 195, "Compact IPX7 waterproof Bluetooth speaker with 360-degree sound.", "5W output, 12h playtime, Built-in carabiner clip.", None),

    # 13-16: Computer Accessories
    ("Block Rock Mechanical Keyboard", "Computer Accessories", "3499.00", 25, True, False, 4.7, 140, "Tactile mechanical keyboard with customizable RGB backlighting and aluminum body.", "Hot-swappable tactile switches, Detachable Type-C cable.", None),
    ("Block Rock Wireless Keyboard", "Computer Accessories", "1799.00", 35, False, True, 4.5, 88, "Slim multi-device wireless keyboard with quiet membrane keys.", "Bluetooth + 2.4G dual wireless, Multi-OS compatibility.", "2299.00"),
    ("Block Rock Precision Mouse", "Computer Accessories", "1299.00", 50, False, False, 4.6, 215, "Ergonomic wireless mouse with high-precision optical sensor.", "4000 DPI, Silent click switches, 18-month battery life.", None),
    ("Block Rock USB-C Hub", "Computer Accessories", "1499.00", 40, False, True, 4.6, 175, "7-in-1 aluminum USB-C multiport adapter with 4K HDMI and 100W PD.", "4K HDMI, 3x USB 3.0, SD/TF card reader, 100W Pass-through.", "1999.00"),

    # 17-20: Gaming
    ("Block Rock RGB Gaming Keyboard", "Gaming", "4999.00", 15, True, True, 4.8, 190, "Tenkeyless mechanical gaming keyboard with optical switches and per-key RGB.", "Linear Optical Switches, PBT Keycaps, N-key rollover.", "5999.00"),
    ("Block Rock Pro Gaming Mouse", "Gaming", "2999.00", 22, True, False, 4.7, 134, "Ultra-lightweight 59g gaming mouse with 26,000 DPI optical sensor.", "PixArt 3395 Sensor, PTFE Skates, Paracord Cable.", None),
    ("Block Rock Gaming Headset", "Gaming", "3499.00", 20, False, True, 4.5, 160, "7.1 surround sound gaming headset with noise-canceling detachable mic.", "50mm Neodymium Drivers, Cross-platform compatibility.", "4199.00"),
    ("Block Rock RGB Mouse Pad", "Gaming", "1199.00", 40, False, False, 4.6, 110, "Extended desk pad with micro-textured cloth surface and 14 RGB lighting modes.", "900x400x4mm size, Non-slip rubber base, Stitched edges.", None),

    # 21-23: Cameras
    ("Block Rock VisionCam 4K", "Cameras", "39999.00", 7, True, False, 4.8, 64, "4K 60fps mirrorless streaming and vlog camera with face-tracking autofocus.", "24.2MP APS-C sensor, Uncropped 4K, Clean HDMI out.", None),
    ("Block Rock ActionCam Pro", "Cameras", "14999.00", 12, False, True, 4.6, 92, "Rugged waterproof action camera with dual color screens and HorizonSteady.", "5.3K 60fps video, 10m waterproof without case, EIS 4.0.", "17999.00"),
    ("Block Rock Compact Camera", "Cameras", "24999.00", 9, False, False, 4.5, 48, "Pocketable point-and-shoot camera with 1-inch sensor and fast f/1.8 lens.", "20.1MP 1-inch CMOS, 3x optical zoom, Flip-up LCD.", None),

    # 24-26: Wearables
    ("Block Rock SmartWatch Pro", "Wearables", "8999.00", 18, True, True, 4.7, 230, "Premium smartwatch with AMOLED display, SpO2 monitoring, and Bluetooth calling.", "1.43-inch AMOLED, Stainless steel bezel, 12-day battery.", "10999.00"),
    ("Block Rock FitWatch", "Wearables", "4499.00", 30, False, False, 4.5, 178, "Fitness tracker watch with built-in GPS and 100+ sports modes.", "1.75-inch HD screen, Continuous HR & Sleep tracking.", None),
    ("Block Rock SmartBand X", "Wearables", "2999.00", 35, False, True, 4.6, 290, "Ultra-light health band with 14-day battery life and swim resistance.", "1.47-inch AMOLED, 5ATM waterproof, Auto workout detection.", "3599.00"),

    # 27-30: Accessories
    ("Block Rock 65W Fast Charger", "Accessories", "1799.00", 50, False, True, 4.8, 310, "Compact Dual USB-C GaN fast wall charger for laptops and phones.", "65W Power Delivery 3.0, Foldable plug, GaN Tech.", "2199.00"),
    ("Block Rock PowerBank 20K", "Accessories", "2499.00", 40, True, False, 4.7, 245, "High-capacity 20,000mAh power bank with 22.5W fast charging.", "Triple output ports, LED digital display, PD 20W input/output.", None),
    ("Block Rock USB-C Cable", "Accessories", "699.00", 100, False, False, 4.6, 420, "Durable 100W braided nylon USB-C to USB-C cable (2 meters).", "100W 5A E-Marker chip, 480Mbps data transfer, Bend tested.", None),
    ("Block Rock Wireless Charger", "Accessories", "1999.00", 45, False, True, 4.5, 180, "Fast 15W Qi wireless charging pad with ambient LED indicator.", "15W Max output, Soft-touch anti-slip finish, Foreign object detection.", "2499.00"),

    # 31-32: Laptops (New)
    ("Block Rock ProBook 16", "Laptops", "79999.00", 10, True, True, 4.9, 88, "Expansive 16-inch workstation laptop for heavy multitasking and software dev.", "16-inch 2.5K 120Hz, Intel Core i9, 32GB RAM, 1TB SSD.", "92999.00"),
    ("Block Rock CreatorBook 14", "Laptops", "69999.00", 12, False, False, 4.7, 54, "Color-accurate 14-inch laptop with 100% DCI-P3 display for photo/video editing.", "14-inch 2.8K OLED, Ryzen 7, 16GB RAM, 512GB SSD.", None),

    # 33-34: Smartphones (New)
    ("Block Rock Fold X", "Smartphones", "74999.00", 7, True, False, 4.8, 42, "Revolutionary foldable smartphone with dual AMOLED screens and zero gap hinge.", "7.6-inch Inner Foldable AMOLED, Snapdragon 8 Gen 3, 12GB RAM.", None),
    ("Block Rock Max 5G", "Smartphones", "39999.00", 18, True, True, 4.7, 125, "Big-battery powerhouse phone with 6.8-inch display and 50MP triple camera.", "6.8-inch 120Hz AMOLED, 6000mAh battery, 80W Turbo charge.", "45999.00"),

    # 35-36: Audio (New)
    ("Block Rock SoundBar Pro", "Audio", "6999.00", 25, True, True, 4.7, 115, "2.1 Channel home theater soundbar with wireless subwoofer and Dolby Audio.", "160W Peak Output, Bluetooth 5.3, HDMI ARC & Optical.", "8499.00"),
    ("Block Rock Wireless Earbuds S", "Audio", "3999.00", 35, False, False, 4.5, 95, "Compact ergonomic earbuds featuring crystal-clear quad-mic ENC for calls.", "Environmental Noise Cancellation, 28h battery, Fast Pair.", None),

    # 37-38: Computer Accessories (New)
    ("Block Rock RGB Mechanical Pro", "Computer Accessories", "5499.00", 20, True, True, 4.8, 78, "Wireless tri-mode mechanical keyboard with gasket mount and custom switches.", "Bluetooth 5.0 / 2.4G / Type-C, Gasket mounted, Hot-swap.", "6499.00"),
    ("Block Rock Ergonomic Mouse", "Computer Accessories", "1999.00", 40, False, False, 4.6, 62, "Vertical ergonomic mouse engineered to reduce forearm twist and wrist strain.", "57-degree vertical angle, Adjustable DPI 800-2400, Silent click.", None),

    # 39-40: Gaming (New)
    ("Block Rock Gaming Controller X", "Gaming", "3999.00", 25, True, True, 4.7, 145, "Wireless gamepad with Hall Effect anti-drift joysticks and customizable triggers.", "Hall Effect Sensors, 1000Hz polling rate, PC/Android/Switch support.", "4799.00"),
    ("Block Rock Gaming Chair", "Gaming", "12999.00", 10, True, False, 4.8, 52, "Ergonomic gaming chair with high-density cold-cured foam and 4D armrests.", "Class-4 Gas Lift, 150-degree recline, Lumbar support pillow.", None),

    # 41-42: Cameras (New)
    ("Block Rock CreatorCam 4K", "Cameras", "49999.00", 6, True, True, 4.9, 38, "Professional cinema vlog camera featuring in-body image stabilization (IBIS).", "Cinema 4K 60p, 5-Axis IBIS, Dual SD card slots.", "57999.00"),
    ("Block Rock VlogCam Mini", "Cameras", "19999.00", 12, False, False, 4.5, 29, "Ultra-compact pocket vlog camera with directional 3-capsule mic and windscreen.", "1-inch 20MP sensor, Bokeh switch, Tally light.", None),

    # 43-44: Wearables (New)
    ("Block Rock SmartWatch Ultra", "Wearables", "11999.00", 15, True, True, 4.9, 84, "Rugged titanium smartwatch with dual-frequency GPS and 100m water rating.", "Titanium case, Sapphire glass, 49mm display, 18-day battery.", "13999.00"),
    ("Block Rock Fitness Band Pro", "Wearables", "3499.00", 30, False, False, 4.6, 110, "Full-screen health tracker featuring ECG analysis and sleep apnea alerts.", "1.62-inch AMOLED, ECG sensor, Continuous SpO2 & Temp.", None),

    # 45-47: Accessories (New)
    ("Block Rock GaN Charger 100W", "Accessories", "3999.00", 35, True, True, 4.8, 160, "Ultra-fast 4-port 100W GaN desktop charger for MacBook, iPad, and phone.", "3x USB-C + 1x USB-A, GaN IV Tech, Intelligent power allocation.", "4999.00"),
    ("Block Rock PowerBank 30K", "Accessories", "3499.00", 25, False, False, 4.6, 88, "Monstrous 30,000mAh laptop battery pack with 65W PD fast charging output.", "65W USB-C PD, Pass-through charging, Heavy duty cell.", None),
    ("Block Rock Thunderbolt Cable", "Accessories", "1499.00", 60, False, True, 4.7, 105, "Certified Thunderbolt 4 cable supporting 40Gbps data and 240W charging.", "40Gbps data speed, 8K video output, 240W EPR charging.", "1899.00"),

    # 48-50: Computer Accessories & Accessories (New)
    ("Block Rock Laptop Stand Pro", "Computer Accessories", "2499.00", 30, False, True, 4.7, 132, "Adjustable aluminum laptop stand with dual silent cooling fans and RGB strip.", "Ergonomic height adjustment, Silent USB dual fans, Foldable.", "2999.00"),
    ("Block Rock Portable SSD 1TB", "Computer Accessories", "7999.00", 20, True, False, 4.9, 140, "Ultra-fast 1050MB/s NVMe USB 3.2 Gen 2 portable solid state drive.", "1050MB/s Read/Write, IP65 water/dust resistance, Drop proof.", None),
    ("Block Rock Smart Home Hub", "Accessories", "4999.00", 18, True, True, 4.6, 74, "Smart home gateway with 7-inch touch panel supporting Zigbee, Thread, and Matter.", "7-inch HD display, Matter & Zigbee 3.0 support, Voice control.", "5999.00"),
]


class Command(BaseCommand):
    help = 'Seed exactly 50 active Block Rock products into the database.'

    def handle(self, *args, **options):
        category_map = {}
        for name, description in CATEGORIES:
            category, created = Category.objects.update_or_create(
                name=name,
                defaults={'description': description, 'is_active': True},
            )
            category_map[name] = category

        seeded_product_names = set()

        for item in PRODUCTS:
            (name, category_name, price_str, stock, is_featured, is_deal,
             rating, review_count, description, short_desc, mrp_str) = item

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
                    'brand': 'Block Rock',
                    'category': category_map[category_name],
                    'description': description,
                    'short_description': short_desc,
                    'price': regular_price,
                    'discount_price': sale_price,
                    'discount': legacy_discount,
                    'stock': stock,
                    'rating': rating,
                    'review_count': review_count,
                    'is_featured': is_featured,
                    'is_deal': is_deal,
                    'is_active': True,
                },
            )
            seeded_product_names.add(name)

        # Deactivate any non-catalog dummy products to ensure active count is exactly 50
        deactivated = Product.objects.exclude(name__in=seeded_product_names).update(is_active=False)

        active_count = Product.objects.filter(is_active=True).count()
        total_count = Product.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(category_map)} categories and {len(seeded_product_names)} Block Rock products.\n'
            f'Deactivated {deactivated} non-catalogue products.\n'
            f'Active product count: {active_count} | Total DB product count: {total_count}'
        ))
