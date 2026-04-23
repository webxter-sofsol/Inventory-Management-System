"""
Management command to seed the database with realistic test data.
Usage: python manage.py seed_data
       python manage.py seed_data --reset   (clears existing data first)
"""
import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from inventory.models import Category, Product, StockTransaction, LowStockAlert

User = get_user_model()


CATEGORIES = [
    ("Electronics",     "Computers, phones, accessories, and gadgets"),
    ("Office Supplies", "Stationery, paper, pens, and desk accessories"),
    ("Furniture",       "Desks, chairs, shelving, and storage"),
    ("Networking",      "Routers, switches, cables, and network hardware"),
    ("Peripherals",     "Keyboards, mice, monitors, and input devices"),
    ("Storage",         "Hard drives, SSDs, USB drives, and memory cards"),
]

PRODUCTS = [
    # (name, category, price, quantity, alert_threshold)
    # Electronics
    ("MacBook Pro 14\"",        "Electronics",     2499.00, 12,  5),
    ("Dell XPS 15",             "Electronics",     1799.00, 8,   3),
    ("iPhone 15 Pro",           "Electronics",     1199.00, 25,  10),
    ("Samsung Galaxy S24",      "Electronics",     999.00,  18,  8),
    ("iPad Air",                "Electronics",     749.00,  3,   5),   # low stock
    ("Sony WH-1000XM5",         "Electronics",     349.00,  0,   5),   # out of stock

    # Office Supplies
    ("A4 Paper (500 sheets)",   "Office Supplies", 8.99,    200, 50),
    ("Ballpoint Pens (12pk)",   "Office Supplies", 4.49,    85,  20),
    ("Sticky Notes (6pk)",      "Office Supplies", 6.99,    4,   15),  # low stock
    ("Stapler",                 "Office Supplies", 14.99,   30,  10),
    ("Whiteboard Markers",      "Office Supplies", 9.99,    12,  10),
    ("Printer Ink Cartridge",   "Office Supplies", 29.99,   2,   8),   # low stock

    # Furniture
    ("Ergonomic Office Chair",  "Furniture",       449.00,  6,   3),
    ("Standing Desk",           "Furniture",       699.00,  4,   2),
    ("Bookshelf (5-tier)",      "Furniture",       189.00,  9,   3),
    ("Filing Cabinet",          "Furniture",       249.00,  1,   3),   # low stock

    # Networking
    ("Cisco Switch 24-port",    "Networking",      899.00,  5,   2),
    ("Ubiquiti Access Point",   "Networking",      179.00,  14,  5),
    ("Cat6 Cable (50m)",        "Networking",      24.99,   40,  10),
    ("Patch Panel 24-port",     "Networking",      89.99,   7,   3),

    # Peripherals
    ("Logitech MX Master 3",    "Peripherals",     99.99,   22,  8),
    ("Mechanical Keyboard",     "Peripherals",     149.99,  15,  5),
    ("Dell 27\" Monitor",       "Peripherals",     399.00,  10,  4),
    ("Webcam 4K",               "Peripherals",     129.99,  3,   5),   # low stock
    ("USB-C Hub 7-in-1",        "Peripherals",     49.99,   0,   5),   # out of stock

    # Storage
    ("Samsung 1TB SSD",         "Storage",         89.99,   35,  10),
    ("WD 4TB HDD",              "Storage",         79.99,   20,  8),
    ("SanDisk 256GB USB",       "Storage",         29.99,   50,  15),
    ("MicroSD 128GB",           "Storage",         18.99,   2,   10),  # low stock
    ("NAS Drive 8TB",           "Storage",         199.99,  6,   3),
]


class Command(BaseCommand):
    help = "Seed the database with realistic inventory test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing inventory data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Clearing existing data...")
            StockTransaction.objects.all().delete()
            LowStockAlert.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Existing inventory data cleared."))

        with transaction.atomic():
            admin = self._create_admin()
            categories = self._create_categories()
            products = self._create_products(categories)
            self._create_transactions(products, admin)
            self._create_alerts(products)

        self.stdout.write(self.style.SUCCESS("\nDatabase seeded successfully!"))
        self.stdout.write(f"  Login: admin@example.com / admin123")

    # ------------------------------------------------------------------

    def _create_admin(self):
        email = "admin@example.com"
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"  Admin user already exists ({email}), skipping.")
            return User.objects.get(email=email)

        user = User.objects.create_superuser(email=email, password="admin123")
        self.stdout.write(self.style.SUCCESS(f"  Created admin: {email}"))
        return user

    def _create_categories(self):
        created = {}
        for name, description in CATEGORIES:
            cat, new = Category.objects.get_or_create(
                name=name,
                defaults={"description": description},
            )
            created[name] = cat
            if new:
                self.stdout.write(f"  Category: {name}")
        self.stdout.write(self.style.SUCCESS(f"  {len(created)} categories ready."))
        return created

    def _create_products(self, categories):
        products = []
        new_count = 0
        for name, cat_name, price, quantity, threshold in PRODUCTS:
            product, new = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": categories[cat_name],
                    "price": Decimal(str(price)),
                    "quantity": quantity,
                    "alert_threshold": threshold,
                },
            )
            products.append(product)
            if new:
                new_count += 1
        self.stdout.write(self.style.SUCCESS(f"  {new_count} products created ({len(products)} total)."))
        return products

    def _create_transactions(self, products, user):
        """Generate ~90 days of realistic transaction history."""
        if StockTransaction.objects.exists():
            self.stdout.write("  Transactions already exist, skipping.")
            return

        now = timezone.now()
        records = []

        for product in products:
            # 3–8 transactions per product spread over the last 90 days
            num_tx = random.randint(3, 8)
            for i in range(num_tx):
                days_ago = random.randint(1, 90)
                tx_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                tx_type = random.choice(["purchase", "purchase", "sale"])  # bias toward purchases
                qty = random.randint(1, 20) if tx_type == "purchase" else random.randint(1, 5)

                records.append(StockTransaction(
                    product=product,
                    user=user,
                    transaction_type=tx_type,
                    quantity_change=qty if tx_type == "purchase" else -qty,
                    timestamp=tx_time,
                ))

        # Bulk insert, then fix auto_now_add timestamps via update
        StockTransaction.objects.bulk_create(records)

        # Update timestamps (bulk_create respects the value when auto_now_add=False,
        # but our field uses auto_now_add so we patch via queryset update per record)
        for obj, rec in zip(
            StockTransaction.objects.order_by("-id")[: len(records)],
            records,
        ):
            StockTransaction.objects.filter(pk=obj.pk).update(timestamp=rec.timestamp)

        self.stdout.write(self.style.SUCCESS(f"  {len(records)} transactions created."))

    def _create_alerts(self, products):
        """Create low-stock alerts for products below their threshold."""
        alert_count = 0
        for product in products:
            if product.quantity < product.alert_threshold:
                _, new = LowStockAlert.objects.get_or_create(
                    product=product,
                    defaults={"is_active": True},
                )
                if new:
                    alert_count += 1
        self.stdout.write(self.style.SUCCESS(f"  {alert_count} low-stock alerts created."))
