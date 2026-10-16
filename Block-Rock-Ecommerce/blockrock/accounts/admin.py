from django.contrib import admin, messages
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html

from .models import MarketingCampaign, MarketingEmailDelivery, PromotionAnnouncement, Subscriber
from .services import publish_promotion


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('email',)
    ordering = ('-subscribed_at',)
    actions = ('mark_active', 'mark_inactive')
    readonly_fields = ('subscribed_at', 'unsubscribe_token', 'welcome_email_sent_at')

    @admin.action(description='Reactivate selected subscribers')
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Deactivate selected subscribers')
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)


class MarketingEmailDeliveryInline(admin.TabularInline):
    model = MarketingEmailDelivery
    extra = 0
    can_delete = False
    fields = ('subscriber', 'status', 'attempts', 'sent_at', 'last_error', 'created_at')
    readonly_fields = fields
    ordering = ('created_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('subject', 'campaign_type', 'status', 'queued_at', 'completed_at')
    list_filter = ('campaign_type', 'status')
    search_fields = ('subject', 'product__name', 'promotion__title')
    readonly_fields = ('campaign_type', 'product', 'promotion', 'subject', 'status', 'queued_at', 'completed_at')
    inlines = (MarketingEmailDeliveryInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PromotionAnnouncement)
class PromotionAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'message')
    readonly_fields = ('is_published', 'published_at', 'email_preview')
    fields = ('title', 'message', 'destination_url', 'image', 'is_published', 'published_at', 'email_preview')
    actions = ('publish_selected_announcements',)

    @admin.display(description='Email preview')
    def email_preview(self, announcement):
        if not announcement or not announcement.pk:
            return 'Save this draft to preview its email content.'
        destination = announcement.destination_url or '/'
        return format_html(
            '<strong>{}</strong><br>{}<br><small>Destination: {}</small>',
            announcement.title,
            linebreaksbr(announcement.message),
            destination,
        )

    @admin.action(description='Publish selected announcements and queue their email')
    def publish_selected_announcements(self, request, queryset):
        queued = 0
        already_published = 0
        for announcement in queryset:
            _, created = publish_promotion(announcement)
            if created:
                queued += 1
            else:
                already_published += 1
        if queued:
            self.message_user(
                request,
                f'{queued} promotional announcement(s) published and queued for delivery.',
                level=messages.SUCCESS,
            )
        if already_published:
            self.message_user(
                request,
                f'{already_published} selected announcement(s) were already published.',
                level=messages.INFO,
            )
