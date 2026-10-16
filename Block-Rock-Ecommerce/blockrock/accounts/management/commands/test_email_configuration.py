from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts.services import _from_email


class Command(BaseCommand):
    help = 'Send one real SMTP configuration test email. Requires valid SMTP credentials.'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='A single recipient email address for the test.')

    def handle(self, *args, **options):
        recipient = options['to'].strip().lower()
        try:
            validate_email(recipient)
        except ValidationError as error:
            raise CommandError('Provide a valid recipient email address.') from error

        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend' and not settings.EMAIL_HOST_PASSWORD:
            raise CommandError('EMAIL_HOST_PASSWORD is not configured. Use a Gmail App Password, never an account password.')

        message = EmailMultiAlternatives(
            subject=f'{settings.EMAIL_FROM_NAME} SMTP configuration test',
            body='This confirms that the Django email configuration can deliver a message.',
            from_email=_from_email(),
            to=[recipient],
        )
        message.attach_alternative(
            '<p>This confirms that the Django email configuration can deliver a message.</p>',
            'text/html',
        )
        try:
            sent_count = message.send(fail_silently=False)
        except Exception as error:
            raise CommandError(f'SMTP test failed: {error.__class__.__name__}') from error

        if not sent_count:
            raise CommandError('SMTP backend accepted no recipients.')
        self.stdout.write(self.style.SUCCESS(f'SMTP test email sent to {recipient}.'))
