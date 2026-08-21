from decimal import Decimal

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


def move_legacy_categories(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.all():
        name = (product.category or '').strip() or 'Uncategorized'
        category, _ = Category.objects.get_or_create(
            name=name,
            defaults={'slug': f'{name.lower().replace(" ", "-")}-{product.pk}' if name == 'Uncategorized' else name.lower().replace(' ', '-')},
        )
        product.category_relation = category
        product.save(update_fields=['category_relation'])


def populate_legacy_slugs(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    used_slugs = set()
    for product in Product.objects.order_by('pk'):
        base = (product.name or 'product').lower().replace(' ', '-')
        slug = base
        suffix = 2
        while slug in used_slugs:
            slug = f'{base}-{suffix}'
            suffix += 1
        used_slugs.add(slug)
        product.slug = slug
        product.save(update_fields=['slug'])


class Migration(migrations.Migration):
    dependencies = [('products', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, upload_to='categories/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name'], 'verbose_name_plural': 'categories'},
        ),
        migrations.AddField(model_name='product', name='category_relation', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.category')),
        migrations.AddField(model_name='product', name='discount_price', field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
        migrations.AddField(model_name='product', name='is_active', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='product', name='is_deal', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='product', name='is_featured', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='product', name='review_count', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='product', name='short_description', field=models.CharField(blank=True, max_length=220)),
        migrations.AddField(model_name='product', name='slug', field=models.SlugField(blank=True, max_length=240, null=True, unique=True)),
        migrations.AddField(model_name='product', name='updated_at', field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(model_name='product', name='discount', field=models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(100)])),
        migrations.AlterField(model_name='product', name='image', field=models.ImageField(blank=True, upload_to='products/')),
        migrations.AlterField(model_name='product', name='price', field=models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
        migrations.AlterField(model_name='product', name='stock', field=models.PositiveIntegerField(default=0)),
        migrations.AlterField(model_name='product', name='rating', field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
        migrations.RunPython(move_legacy_categories, migrations.RunPython.noop),
        migrations.RunPython(populate_legacy_slugs, migrations.RunPython.noop),
        migrations.RemoveField(model_name='product', name='category'),
        migrations.RenameField(model_name='product', old_name='category_relation', new_name='category'),
        migrations.AlterField(model_name='product', name='category', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='products.category')),
        migrations.AlterField(model_name='product', name='slug', field=models.SlugField(blank=True, max_length=240, unique=True)),
        migrations.AlterModelOptions(name='product', options={'ordering': ['-created_at', 'name']}),
    ]
