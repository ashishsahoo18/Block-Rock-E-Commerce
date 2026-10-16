import uuid

from django.db import models
from django.db.models import Q


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-subscribed_at']

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class PromotionAnnouncement(models.Model):
    """An administrator-authored promotional email draft.

    Saving a draft never sends email. It must be explicitly published from
    Django Admin, which queues a campaign in the persistent outbox.
    """

    title = models.CharField(max_length=200)
    message = models.TextField()
    destination_url = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='promotions/', blank=True)
    is_published = models.BooleanField(default=False, editable=False)
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'title']

    def __str__(self):
        return self.title


class MarketingCampaign(models.Model):
    """A durable, deduplicated request to send a marketing announcement."""

    class CampaignType(models.TextChoices):
        PRODUCT = 'product', 'New product'
        PROMOTION = 'promotion', 'Promotion'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        COMPLETED = 'completed', 'Completed'
        PARTIAL = 'partial', 'Partially delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    campaign_type = models.CharField(max_length=16, choices=CampaignType.choices)
    product = models.OneToOneField(
        'products.Product',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='newsletter_campaign',
    )
    promotion = models.OneToOneField(
        PromotionAnnouncement,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='newsletter_campaign',
    )
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    queued_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-queued_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(product__isnull=False, promotion__isnull=True)
                    | Q(product__isnull=True, promotion__isnull=False)
                ),
                name='marketing_campaign_has_one_source',
            ),
        ]

    def __str__(self):
        return f'{self.get_campaign_type_display()}: {self.subject}'


class MarketingEmailDelivery(models.Model):
    """Per-subscriber outbox record; recipients are never exposed to each other."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='deliveries')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='marketing_deliveries')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=('campaign', 'subscriber'), name='unique_campaign_subscriber_delivery'),
        ]

    def __str__(self):
        return f'{self.campaign_id} / subscriber {self.subscriber_id} ({self.get_status_display()})'
