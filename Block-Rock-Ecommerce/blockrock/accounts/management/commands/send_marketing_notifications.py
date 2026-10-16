from django.core.management.base import BaseCommand, CommandError

from accounts.services import deliver_pending_campaigns


class Command(BaseCommand):
    help = 'Deliver queued newsletter campaigns through the configured Django email backend.'

    def add_arguments(self, parser):
        parser.add_argument('--campaign-id', type=int, help='Deliver only one queued campaign.')
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry delivery records that previously failed. Sent recipients are never resent.',
        )

    def handle(self, *args, **options):
        campaign_id = options.get('campaign_id')
        try:
            totals = deliver_pending_campaigns(
                retry_failed=options['retry_failed'],
                campaign_id=campaign_id,
            )
        except Exception as error:
            raise CommandError(f'Unable to process the marketing outbox: {error.__class__.__name__}') from error

        self.stdout.write(
            self.style.SUCCESS(
                'Processed {campaigns} campaign(s): {sent} sent, {failed} failed, {skipped} skipped.'.format(**totals)
            )
        )
