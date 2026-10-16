# Email notifications

Copy `.env.example` to `.env` in this directory and set `EMAIL_HOST_PASSWORD` to a Gmail **App Password** generated for `sahooashish673@gmail.com`. Do not use or store the normal Gmail password. The `.env` file is ignored by Git, and deployment environments may provide the same variables directly instead.

Set `SITE_URL` to the public HTTPS site address before sending customer email. Set `NEWSLETTER_SEND_WELCOME_EMAIL=True` when welcome messages should be delivered after subscription.

New active products created in Django Admin queue one product campaign. The Product admin action can explicitly queue an announcement for another active product. Promotional announcements are saved as drafts in **Promotion announcements**; use the explicit **Publish selected announcements and queue their email** action to publish them. Drafts never send email.

Queued campaigns are stored in the database and must be processed outside web requests:

```powershell
python manage.py send_marketing_notifications
```

Schedule that command with your deployment scheduler (for example, cron or Windows Task Scheduler). It sends one message per active subscriber, records each result, excludes inactive subscribers, and never resends a delivery already marked sent. Failed records remain available for an intentional retry:

```powershell
python manage.py send_marketing_notifications --retry-failed
```

For this local Windows development environment, `scripts/run_marketing_outbox.cmd` runs the command with the project's configured Python runtime. The **Block Rock Newsletter Delivery** scheduled task invokes it every five minutes while you are signed in. It only processes campaigns that were explicitly queued from Django Admin.

Before claiming live delivery works, configure the Gmail App Password and send one real email to an address you control:

```powershell
python manage.py test_email_configuration --to your-test-address@example.com
```

Every marketing message includes an unguessable unsubscribe link. The link shows a confirmation page; only its CSRF-protected POST action deactivates the subscription.
