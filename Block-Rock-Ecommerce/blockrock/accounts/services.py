"""Newsletter email rendering and durable outbox delivery helpers."""

import logging
from email.utils import formataddr
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import MarketingCampaign, MarketingEmailDelivery, PromotionAnnouncement, Subscriber


logger = logging.getLogger(__name__)


def _absolute_url(path):
    return urljoin(f'{settings.SITE_URL.rstrip("/")}/', path.lstrip('/'))


def _from_email():
    return formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL))


def unsubscribe_url(subscriber):
    return _absolute_url(reverse('newsletter_unsubscribe', kwargs={'token': subscriber.unsubscribe_token}))


def _image_url(image_url):
    return _absolute_url(image_url) if image_url else ''


def _send_email(*, subject, text_template, html_template, context, recipient):
    """Send one privacy-safe, multipart message to one recipient."""
    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=_from_email(),
        to=[recipient],
        headers={'List-Unsubscribe': f'<{context["unsubscribe_url"]}>'},
    )
    message.attach_alternative(html_body, 'text/html')
    return message.send(fail_silently=False)


def send_welcome_email(subscriber):
    """Send a single welcome email without making subscription persistence depend on SMTP."""
    if (
        not settings.NEWSLETTER_SEND_WELCOME_EMAIL
        or not subscriber.is_active
        or subscriber.welcome_email_sent_at is not None
    ):
        return False

    context = {
        'brand_name': settings.EMAIL_FROM_NAME,
        'unsubscribe_url': unsubscribe_url(subscriber),
    }
    try:
        sent_count = _send_email(
            subject=f'Welcome to {settings.EMAIL_FROM_NAME}',
            text_template='emails/welcome_email.txt',
            html_template='emails/welcome_email.html',
            context=context,
            recipient=subscriber.email,
        )
    except Exception as error:  # SMTP failures must not undo a valid subscription.
        logger.warning('Newsletter welcome email failed (%s).', error.__class__.__name__)
        return False

    if sent_count:
        Subscriber.objects.filter(
            pk=subscriber.pk,
            welcome_email_sent_at__isnull=True,
        ).update(welcome_email_sent_at=timezone.now())
        return True
    return False


def queue_product_campaign(product):
    """Queue a one-time product campaign; no email is sent during an admin request."""
    if not product.is_active:
        return None, False
    return MarketingCampaign.objects.get_or_create(
        product=product,
        defaults={
            'campaign_type': MarketingCampaign.CampaignType.PRODUCT,
            'subject': f'New from {settings.EMAIL_FROM_NAME}: {product.name}',
        },
    )


def publish_promotion(promotion):
    """Mark a saved draft as published and queue its single corresponding campaign."""
    with transaction.atomic():
        promotion = PromotionAnnouncement.objects.select_for_update().get(pk=promotion.pk)
        if promotion.is_published:
            campaign, _ = MarketingCampaign.objects.get_or_create(
                promotion=promotion,
                defaults={
                    'campaign_type': MarketingCampaign.CampaignType.PROMOTION,
                    'subject': f'{settings.EMAIL_FROM_NAME}: {promotion.title}',
                },
            )
            return campaign, False

        promotion.is_published = True
        promotion.published_at = timezone.now()
        promotion.save(update_fields=('is_published', 'published_at', 'updated_at'))
        campaign, created = MarketingCampaign.objects.get_or_create(
            promotion=promotion,
            defaults={
                'campaign_type': MarketingCampaign.CampaignType.PROMOTION,
                'subject': f'{settings.EMAIL_FROM_NAME}: {promotion.title}',
            },
        )
    return campaign, created


def _queue_initial_deliveries(campaign):
    """Snapshot active recipients once when a campaign is first processed."""
    if campaign.status != MarketingCampaign.Status.QUEUED:
        return

    subscriber_ids = Subscriber.objects.filter(is_active=True).values_list('pk', flat=True)
    MarketingEmailDelivery.objects.bulk_create(
        [MarketingEmailDelivery(campaign=campaign, subscriber_id=subscriber_id) for subscriber_id in subscriber_ids],
        ignore_conflicts=True,
    )
    campaign.status = MarketingCampaign.Status.SENDING
    campaign.save(update_fields=('status',))


def _campaign_is_publishable(campaign):
    if campaign.campaign_type == MarketingCampaign.CampaignType.PRODUCT:
        return campaign.product is not None and campaign.product.is_active
    return campaign.promotion is not None and campaign.promotion.is_published


def _context_for_campaign(campaign, subscriber):
    context = {
        'brand_name': settings.EMAIL_FROM_NAME,
        'unsubscribe_url': unsubscribe_url(subscriber),
    }
    if campaign.campaign_type == MarketingCampaign.CampaignType.PRODUCT:
        product = campaign.product
        context.update({
            'product': product,
            'product_url': _absolute_url(reverse('product_detail', kwargs={'slug': product.slug})),
            'product_image_url': _image_url(product.primary_image_url),
        })
        return 'emails/product_announcement.txt', 'emails/product_announcement.html', context

    promotion = campaign.promotion
    destination_url = promotion.destination_url or '/'
    context.update({
        'promotion': promotion,
        'destination_url': _absolute_url(destination_url),
        'promotion_image_url': _image_url(promotion.image.url if promotion.image else ''),
    })
    return 'emails/promotion_announcement.txt', 'emails/promotion_announcement.html', context


def _mark_campaign_cancelled(campaign):
    MarketingEmailDelivery.objects.filter(
        campaign=campaign,
        status=MarketingEmailDelivery.Status.PENDING,
    ).update(status=MarketingEmailDelivery.Status.SKIPPED, last_error='Campaign was no longer publishable.')
    campaign.status = MarketingCampaign.Status.CANCELLED
    campaign.completed_at = timezone.now()
    campaign.save(update_fields=('status', 'completed_at'))


def deliver_campaign(campaign, *, retry_failed=False):
    """Deliver a queued campaign through the configured Django email backend.

    One delivery record is sent at a time, which keeps addresses private and
    makes successful deliveries idempotent across future command runs.
    """
    if campaign.status in (MarketingCampaign.Status.COMPLETED, MarketingCampaign.Status.CANCELLED):
        return {'sent': 0, 'failed': 0, 'skipped': 0}

    if not _campaign_is_publishable(campaign):
        _mark_campaign_cancelled(campaign)
        return {'sent': 0, 'failed': 0, 'skipped': 0}

    _queue_initial_deliveries(campaign)
    statuses = [MarketingEmailDelivery.Status.PENDING]
    if retry_failed:
        statuses.append(MarketingEmailDelivery.Status.FAILED)

    sent = failed = skipped = 0
    deliveries = MarketingEmailDelivery.objects.select_related('subscriber').filter(
        campaign=campaign,
        status__in=statuses,
    )
    for delivery in deliveries:
        if not delivery.subscriber.is_active:
            delivery.status = MarketingEmailDelivery.Status.SKIPPED
            delivery.last_error = 'Subscriber is inactive.'
            delivery.save(update_fields=('status', 'last_error', 'updated_at'))
            skipped += 1
            continue

        text_template, html_template, context = _context_for_campaign(campaign, delivery.subscriber)
        delivery.attempts += 1
        try:
            sent_count = _send_email(
                subject=campaign.subject,
                text_template=text_template,
                html_template=html_template,
                context=context,
                recipient=delivery.subscriber.email,
            )
        except Exception as error:  # Record a safe error marker and allow a deliberate retry.
            delivery.status = MarketingEmailDelivery.Status.FAILED
            delivery.last_error = f'Email backend error: {error.__class__.__name__}'
            delivery.save(update_fields=('status', 'last_error', 'attempts', 'updated_at'))
            logger.warning(
                'Marketing delivery %s failed (%s).',
                delivery.pk,
                error.__class__.__name__,
            )
            failed += 1
            continue

        if sent_count:
            delivery.status = MarketingEmailDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ''
            delivery.save(update_fields=('status', 'sent_at', 'last_error', 'attempts', 'updated_at'))
            sent += 1
        else:
            delivery.status = MarketingEmailDelivery.Status.FAILED
            delivery.last_error = 'Email backend accepted no recipients.'
            delivery.save(update_fields=('status', 'last_error', 'attempts', 'updated_at'))
            failed += 1

    if campaign.deliveries.filter(status=MarketingEmailDelivery.Status.FAILED).exists():
        campaign.status = MarketingCampaign.Status.PARTIAL
        campaign.completed_at = None
    else:
        campaign.status = MarketingCampaign.Status.COMPLETED
        campaign.completed_at = timezone.now()
    campaign.save(update_fields=('status', 'completed_at'))
    return {'sent': sent, 'failed': failed, 'skipped': skipped}


def deliver_pending_campaigns(*, retry_failed=False, campaign_id=None):
    statuses = [MarketingCampaign.Status.QUEUED, MarketingCampaign.Status.SENDING]
    if retry_failed:
        statuses.append(MarketingCampaign.Status.PARTIAL)
    campaigns = MarketingCampaign.objects.filter(status__in=statuses).select_related('product', 'promotion')
    if campaign_id is not None:
        campaigns = campaigns.filter(pk=campaign_id)

    totals = {'campaigns': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
    for campaign in campaigns:
        result = deliver_campaign(campaign, retry_failed=retry_failed)
        totals['campaigns'] += 1
        for key in ('sent', 'failed', 'skipped'):
            totals[key] += result[key]
    return totals
