from django.contrib import admin

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('email',)
    ordering = ('-subscribed_at',)
    actions = ('mark_active', 'mark_inactive')

    @admin.action(description='Reactivate selected subscribers')
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Deactivate selected subscribers')
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
