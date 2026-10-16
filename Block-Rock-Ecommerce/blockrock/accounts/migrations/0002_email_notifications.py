import uuid

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def populate_unsubscribe_tokens(apps, schema_editor):
    Subscriber = apps.get_model('accounts', 'Subscriber')
    for subscriber in Subscriber.objects.filter(unsubscribe_token__isnull=True).iterator():
        subscriber.unsubscribe_token = uuid.uuid4()
        subscriber.save(update_fields=('unsubscribe_token',))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('products', '0004_banner_product_compare_at_price_productimage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriber',
            name='unsubscribe_token',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='welcome_email_sent_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_unsubscribe_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='subscriber',
            name='unsubscribe_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name='PromotionAnnouncement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('destination_url', models.CharField(blank=True, max_length=255)),
                ('image', models.ImageField(blank=True, upload_to='promotions/')),
                ('is_published', models.BooleanField(default=False, editable=False)),
                ('published_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at', 'title'],
            },
        ),
        migrations.CreateModel(
            name='MarketingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('campaign_type', models.CharField(choices=[('product', 'New product'), ('promotion', 'Promotion')], max_length=16)),
                ('subject', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('sending', 'Sending'), ('completed', 'Completed'), ('partial', 'Partially delivered'), ('cancelled', 'Cancelled')], default='queued', max_length=16)),
                ('queued_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('product', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='newsletter_campaign', to='products.product')),
                ('promotion', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='newsletter_campaign', to='accounts.promotionannouncement')),
            ],
            options={
                'ordering': ['-queued_at'],
            },
        ),
        migrations.CreateModel(
            name='MarketingEmailDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=16)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='accounts.marketingcampaign')),
                ('subscriber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_deliveries', to='accounts.subscriber')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='marketingcampaign',
            constraint=models.CheckConstraint(
                condition=(
                    Q(product__isnull=False, promotion__isnull=True)
                    | Q(product__isnull=True, promotion__isnull=False)
                ),
                name='marketing_campaign_has_one_source',
            ),
        ),
        migrations.AddConstraint(
            model_name='marketingemaildelivery',
            constraint=models.UniqueConstraint(fields=('campaign', 'subscriber'), name='unique_campaign_subscriber_delivery'),
        ),
    ]
