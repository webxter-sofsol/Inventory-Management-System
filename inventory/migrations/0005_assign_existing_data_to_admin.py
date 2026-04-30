from django.db import migrations


def assign_to_admin(apps, schema_editor):
    """
    Assign all Category and Product rows that have no owner (user=NULL)
    to the first superuser found. If no superuser exists, fall back to
    the user with the lowest primary key.
    """
    User = apps.get_model('accounts', 'CustomUser')
    Category = apps.get_model('inventory', 'Category')
    Product = apps.get_model('inventory', 'Product')

    # Pick the admin: prefer admin@example.com, then any superuser, then earliest user
    admin = (
        User.objects.filter(email='admin@example.com').first()
        or User.objects.filter(is_superuser=True).order_by('id').first()
        or User.objects.order_by('id').first()
    )

    if admin is None:
        # No users at all — nothing to assign
        return

    updated_categories = Category.objects.filter(user__isnull=True).update(user=admin)
    updated_products = Product.objects.filter(user__isnull=True).update(user=admin)

    print(
        f"\n  Assigned {updated_categories} categories and "
        f"{updated_products} products to user '{admin.email}' (id={admin.id})"
    )


def reverse_assign(apps, schema_editor):
    """Reverse: set user back to NULL for records owned by the admin."""
    User = apps.get_model('accounts', 'CustomUser')
    Category = apps.get_model('inventory', 'Category')
    Product = apps.get_model('inventory', 'Product')

    admin = (
        User.objects.filter(is_superuser=True).order_by('id').first()
        or User.objects.order_by('id').first()
    )

    if admin is None:
        return

    Category.objects.filter(user=admin).update(user=None)
    Product.objects.filter(user=admin).update(user=None)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_add_user_to_category_and_product'),
    ]

    operations = [
        migrations.RunPython(assign_to_admin, reverse_code=reverse_assign),
    ]
