from decimal import Decimal

from django.core.management.base import BaseCommand

from products.models import Category, Product


CATEGORIES = [
    ('Smartphones', 'Flagship smartphones, everyday essentials, and mobile accessories.'),
    ('Laptops', 'Portable power for work, study, and creative projects.'),
    ('Headphones', 'Immersive listening for focus, travel, and play.'),
    ('Smartwatches', 'Smart health and activity companions for your wrist.'),
    ('Cameras', 'Capture sharp memories, stories, and creative work.'),
    ('Gaming', 'Responsive gear built for more enjoyable play.'),
    ('Accessories', 'Useful extras to complete your setup.'),
    ('Audio', 'Speakers and sound systems that fill the room.'),
]

PRODUCTS = [
    ('Samsung Galaxy S24 Ultra', 'Samsung', 'Smartphones', 'A powerful, precision-built flagship for photography and productivity.', 'Titanium design, versatile camera system, and all-day performance.', '129999.00', '114999.00', 18, 4.8, 246, True, True),
    ('MacBook Air M3', 'Apple', 'Laptops', 'Thin, quiet, and brilliantly capable for work and creative flow.', '13-inch everyday performance laptop with an M3 chip.', '114900.00', '104900.00', 13, 4.9, 189, True, False),
    ('Sony WH-1000XM5', 'Sony', 'Headphones', 'Industry-leading noise cancellation with warm, detailed sound.', 'Wireless ANC headphones built for focused listening.', '34990.00', '29990.00', 14, 4.8, 328, True, True),
    ('Apple Watch Series 9', 'Apple', 'Smartwatches', 'A smarter way to stay active, connected, and in tune with your day.', 'Bright display and meaningful wellness features.', '41900.00', None, 22, 4.7, 151, True, False),
    ('iPhone 16 Pro', 'Apple', 'Smartphones', 'A pro-grade mobile camera and high-performance everyday companion.', 'Premium smartphone with advanced photography tools.', '119900.00', None, 10, 4.8, 211, False, False),
    ('Dell XPS 15', 'Dell', 'Laptops', 'A creator-friendly laptop with a vivid display and serious power.', '15-inch performance laptop for demanding projects.', '149990.00', '136990.00', 7, 4.6, 84, False, False),
    ('Canon EOS R50', 'Canon', 'Cameras', 'An approachable mirrorless camera for polished photos and videos.', 'Compact creator camera with an interchangeable-lens system.', '74995.00', '67995.00', 12, 4.7, 96, False, True),
    ('Pulse Wireless Controller', 'Block Rock', 'Gaming', 'Comfortable wireless control with responsive triggers and tactile feedback.', 'Rechargeable controller for longer weekend sessions.', '5999.00', None, 30, 4.5, 73, False, False),
    ('Orbit Mini Speaker', 'Block Rock', 'Audio', 'Room-filling wireless sound in a compact, travel-ready shape.', 'Portable Bluetooth speaker with rich balanced sound.', '7999.00', '6499.00', 20, 4.6, 104, False, False),
    ('MagSafe Power Bank', 'Block Rock', 'Accessories', 'Snap-on portable power for your compatible phone.', 'Slim magnetic battery pack for an extra boost.', '3999.00', None, 40, 4.4, 57, False, False),
]


class Command(BaseCommand):
    help = 'Create or update sample Block Rock product catalogue data.'

    def handle(self, *args, **options):
        category_map = {}
        for name, description in CATEGORIES:
            category, created = Category.objects.update_or_create(
                name=name,
                defaults={'description': description, 'is_active': True},
            )
            category_map[name] = category

        for (name, brand, category_name, description, short_description, price,
             discount_price, stock, rating, review_count, is_featured, is_deal) in PRODUCTS:
            regular_price = Decimal(price)
            sale_price = Decimal(discount_price) if discount_price else None
            legacy_discount = int(((regular_price - sale_price) / regular_price) * 100) if sale_price else 0
            Product.objects.update_or_create(
                name=name,
                defaults={
                    'brand': brand,
                    'category': category_map[category_name],
                    'description': description,
                    'short_description': short_description,
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

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(CATEGORIES)} categories and {len(PRODUCTS)} products. Safe to run again.'
        ))
