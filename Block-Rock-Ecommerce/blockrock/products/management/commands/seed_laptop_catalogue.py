"""Seed the curated laptop catalogue without touching legacy products."""

from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction

from products.laptop_catalogue import LAPTOP_CATEGORY_NAME, LAPTOPS
from products.models import Category, Product


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
)
IMAGE_META_PATTERNS = (
    r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
)
IMAGE_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
BRAND_IMAGE_FALLBACKS = {
    "HP": (
        "https://hp.widen.net/content/ngot4aivlx/png/ngot4aivlx.png?color=ffffff00&dpi=72&h=600&w=800",
        "https://www.hp.com/emea_middle_east-ar/products/laptops/product-details/2102726020",
    ),
    "Dell": (
        "https://www.dellonline.co.za/cdn/shop/files/31d8a09c-4bdf-4d47-953b-b0270b1f08de-1.jpg?v=1736939232",
        "https://www.dellonline.co.za/products/dell-latitude-7450-14-inch-core-ultra-7-165u-16gb-ram-512gb-ssd-5g-win-11-pro-laptop-315899",
    ),
    "Lenovo": (
        "https://psrefstuff.lenovo.com/syspool/Sys/Image/ThinkPad/ThinkPad_X1_Carbon_Gen_12/ThinkPad_X1_Carbon_Gen_12_CT1_03.png",
        "https://psref.lenovo.com/Product/ThinkPad_X1_Carbon_Gen_12?tab=spec",
    ),
    "Acer": (
        "https://www.notebookcheck.net/uploads/tx_nbc2/Acer_Swift_Go_14_SFG14-72.jpg",
        "https://www.notebookcheck.net/Acer-Swift-Go-14-SFG14-72.817257.0.html",
    ),
    "Apple MacBook": (
        "https://cdn1.waltons.co.za/product-images/2025/AL988022/13-inch-macbook-air-apple-m3-chip-with-8-core-cpu-and-10-core-gpu-16gb-512gb-ssd-silver-1024x1024.webp",
        "https://www.waltons.co.za/buy/13-inch-macbook-air-apple-m3-chip-with-8-core-cpu-and-10-core-gpu-16gb-512gb-ssd-silver",
    ),
    "MSI": (
        "https://www.static-src.com/wcsstore/Indraprastha/images/catalog/full/catalog-image/MTA-170182701/msi_msi_modern_14_c13m_1046_1049_notebook_-core_i7_1355u-16gb-512gb_ssd-14-_fhd_ips-win_11_home_-_ohs_2021-_full01_vuni3tj9.jpg",
        "https://www.blibli.com/p/msi-modern-14-c13m-1046-1049-notebook-core-i7-1355u-16gb-512gb-ssd-14-fhd-ips-win-11-home-ohs-2021/ps--SOM-60023-04755",
    ),
    "Samsung": (
        "https://sinsungcns.com/data/_custom/cus_bbs/_mig/not_specified/20250310182834727130383.png",
        "https://sinsungcns.com/goods/view?no=4008",
    ),
    "Microsoft Surface": (
        "https://hnau.imgix.net/media/catalog/product/s/u/surface-laptop-5-graphite-5_1_4.jpg",
        "https://www.harveynorman.com.au/microsoft-surface-laptop-5-13-5-inch-i5-1235u-16gb-512gb-ssd-laptop-graphite.html",
    ),
    "LG": (
        "https://media.us.lg.com/transform/ecomm-PDPGallery-1100x730/7a4f0d6c-6442-4ec1-950d-1e53a27aee61/16Z90S-G-ADB9U1_gallery_03_5000x5000?io=transform%3Afill%2Cwidth%3A1536",
        "https://www.lg.com/us/laptops/lg-16z90s-g.adb9u1-gram-laptop",
    ),
}


class Command(BaseCommand):
    help = (
        "Seed exactly 50 active laptops without deleting or changing legacy products. "
        "Pass --download-images on the initial run to retrieve the documented product images."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--download-images",
            action="store_true",
            help="Download fresh product images from the documented source pages before seeding.",
        )
        parser.add_argument(
            "--check-sources",
            action="store_true",
            help="Validate image source pages only; do not write to the database or media storage.",
        )

    def _image_source_url(self, page_url):
        request = Request(page_url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        with urlopen(request, timeout=12) as response:
            page = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")

        for pattern in IMAGE_META_PATTERNS:
            match = re.search(pattern, page, flags=re.IGNORECASE)
            if match:
                return urljoin(page_url, html.unescape(match.group(1)))
        raise CommandError(f"No Open Graph product image found at {page_url}")

    def _download_direct_image(self, image_url):
        request = Request(image_url, headers={"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8"})
        with urlopen(request, timeout=20) as response:
            image_bytes = response.read()

        # AVIF is browser-supported and can be served by Django's media view, but
        # many Pillow builds do not include an AVIF decoder. Detect it by its ISO
        # base-media file signature before using Pillow for the common formats.
        if len(image_bytes) >= 12 and image_bytes[4:8] == b"ftyp" and image_bytes[8:12] in {b"avif", b"avis"}:
            return image_bytes, "avif"

        try:
            from PIL import Image

            parsed = Image.open(BytesIO(image_bytes))
            image_format = parsed.format
            parsed.verify()
        except Exception as exc:  # Pillow exposes several image-decoding exceptions.
            raise CommandError(f"Image downloaded for {item['name']} is invalid: {exc}") from exc

        extension = IMAGE_EXTENSIONS.get(image_format)
        if not extension:
            raise CommandError(
                f"Unsupported image format {image_format!r} for {item['name']}. "
                "Use JPEG, PNG, or WebP source imagery."
            )

        return image_bytes, extension

    def _duckduckgo_image_candidates(self, item):
        """Return public product-image candidates when a vendor blocks automation."""
        from urllib.parse import quote

        query = f"{item['name']} laptop product image"
        headers = {"User-Agent": USER_AGENT, "Referer": "https://duckduckgo.com/"}
        search_url = "https://duckduckgo.com/?q=" + quote(query)
        with urlopen(Request(search_url, headers=headers), timeout=12) as response:
            page = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        match = re.search(r"vqd=['\"]([^'\"]+)", page)
        if not match:
            raise CommandError(f"Image fallback search did not return a token for {item['name']}.")

        api_url = (
            "https://duckduckgo.com/i.js?l=us-en&o=json&q="
            + quote(query)
            + "&vqd="
            + quote(match.group(1))
        )
        with urlopen(Request(api_url, headers=headers), timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [
            (result.get("image"), result.get("url"))
            for result in payload.get("results", [])[:10]
            if result.get("image") and result.get("url")
        ]

    def _download_vendor_image(self, item):
        image_url = self._image_source_url(item["image_source_page"])
        image_bytes, extension = self._download_direct_image(image_url)
        return {
            "content": image_bytes,
            "filename": f"laptops/{item['slug']}.{extension}",
            "source_url": image_url,
            "source_page": item["image_source_page"],
            "source_method": "source page Open Graph metadata",
        }

    def _download_fallback_image(self, item, vendor_error):
        candidate_errors = []
        brand_fallback = BRAND_IMAGE_FALLBACKS.get(item["brand"])
        if brand_fallback:
            fallback_url, fallback_page = brand_fallback
            try:
                image_bytes, extension = self._download_direct_image(fallback_url)
                return {
                    "content": image_bytes,
                    "filename": f"laptops/{item['slug']}.{extension}",
                    "source_url": fallback_url,
                    "source_page": fallback_page,
                    "source_method": "documented brand-family fallback",
                }
            except Exception as exc:
                candidate_errors.append(str(exc))
        for candidate_url, candidate_page in self._duckduckgo_image_candidates(item):
            try:
                image_bytes, extension = self._download_direct_image(candidate_url)
                return {
                    "content": image_bytes,
                    "filename": f"laptops/{item['slug']}.{extension}",
                    "source_url": candidate_url,
                    "source_page": candidate_page,
                    "source_method": "product-image search fallback",
                }
            except Exception as exc:
                candidate_errors.append(str(exc))
        raise CommandError(
            f"Could not import an image for {item['name']}. "
            f"Vendor source failed: {vendor_error}; fallback errors: {candidate_errors[:3]}"
        )

    def _preflight_images(self):
        downloaded = {}
        failures = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self._download_vendor_image, item): (index, item)
                for index, item in enumerate(LAPTOPS, start=1)
            }
            for future in as_completed(futures):
                index, item = futures[future]
                try:
                    downloaded[item["slug"]] = future.result()
                    self.stdout.write(f"[{index:02d}/{len(LAPTOPS)}] verified image: {item['name']}")
                except Exception as exc:
                    failures.append((index, item, exc))

        # DuckDuckGo issues short-term rate limits under concurrent image API load,
        # so fallbacks deliberately run one at a time. They are only used for
        # vendors that blocked or timed out on direct product-page access.
        fallback_failures = []
        for index, item, vendor_error in sorted(failures, key=lambda row: row[0]):
            try:
                downloaded[item["slug"]] = self._download_fallback_image(item, vendor_error)
                self.stdout.write(f"[{index:02d}/{len(LAPTOPS)}] verified fallback image: {item['name']}")
            except Exception as exc:
                fallback_failures.append(f"{item['name']}: {exc}")

        if fallback_failures:
            raise CommandError("Image source validation failed:\n- " + "\n- ".join(fallback_failures))
        return downloaded

    def _write_source_manifest(self, downloaded_images):
        if not downloaded_images:
            return
        manifest = []
        for item in LAPTOPS:
            image = downloaded_images[item["slug"]]
            manifest.append({
                "slug": item["slug"],
                "name": item["name"],
                "brand": item["brand"],
                "image_file": f"products/{image['filename']}",
                "specification_source": item["spec_source"],
                "image_source_page": image["source_page"],
                "image_source_url": image["source_url"],
                "image_source_method": image["source_method"],
            })
        manifest_path = settings.MEDIA_ROOT / "products" / "laptops" / "sources.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def handle(self, *args, **options):
        if len(LAPTOPS) != 50:
            raise CommandError("The laptop source data must contain exactly 50 products.")

        downloaded_images = None
        if options["download_images"] or options["check_sources"]:
            downloaded_images = self._preflight_images()
            if options["check_sources"]:
                self.stdout.write(self.style.SUCCESS(f"Validated {len(downloaded_images)} product image sources."))
                return

        category, _ = Category.objects.get_or_create(
            name=LAPTOP_CATEGORY_NAME,
            defaults={
                "slug": "laptops",
                "description": "Laptops for study, work, creative projects, and gaming.",
                "is_active": True,
                "is_ingot_original": False,
            },
        )
        catalogue_slugs = {item["slug"] for item in LAPTOPS}
        other_active_laptops = (
            Product.objects.filter(category=category, is_active=True)
            .exclude(slug__in=catalogue_slugs)
        )
        if other_active_laptops.exists():
            names = ", ".join(other_active_laptops.values_list("name", flat=True)[:5])
            raise CommandError(
                "Refusing to change the active laptop catalogue because unrelated active laptop "
                f"records already exist: {names}. Archive or move those records in Django Admin first."
            )

        seeded = 0
        created = 0
        with transaction.atomic():
            for item in LAPTOPS:
                product, was_created = Product.objects.update_or_create(
                    slug=item["slug"],
                    defaults={
                        "name": item["name"],
                        "brand": item["brand"],
                        "category": category,
                        "description": item["description"],
                        "short_description": item["short_description"],
                        "price": item["compare_at_price"],
                        "discount_price": item["price"],
                        "compare_at_price": item["compare_at_price"],
                        "discount": int(
                            (1 - (float(item["price"]) / float(item["compare_at_price"]))) * 100
                        ),
                        "stock": item["stock"],
                        "rating": 0,
                        "review_count": 0,
                        "is_featured": item["is_featured"],
                        "is_deal": item["is_deal"],
                        "is_ingot_original": False,
                        "is_active": True,
                    },
                )
                if downloaded_images:
                    source_image = downloaded_images[item["slug"]]
                    if product.image.name.startswith("products/laptops/"):
                        default_storage.delete(product.image.name)
                    product.image.save(
                        source_image["filename"],
                        ContentFile(source_image["content"]),
                        save=True,
                    )
                elif not product.image:
                    self.stdout.write(self.style.WARNING(
                        f"{product.name} was seeded without a local image. "
                        "Run again with --download-images to complete media import."
                    ))
                seeded += 1
                created += int(was_created)

            active_laptop_count = Product.objects.filter(category=category, is_active=True).count()
            if active_laptop_count != 50:
                raise CommandError(
                    f"Expected 50 active laptop products after seeding, found {active_laptop_count}."
                )

        self._write_source_manifest(downloaded_images)
        active_laptops = Product.objects.filter(category=category, is_active=True)
        missing_images = active_laptops.filter(image="").count()
        if missing_images:
            self.stdout.write(self.style.WARNING(
                f"Seeded {seeded} products ({created} new), but {missing_images} have no local image."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Seeded {seeded} products ({created} new). Active laptop catalogue: 50 products."
            ))
