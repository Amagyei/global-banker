from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'first_name',
        'last_name',
        'phone',
        'country_code',
        'time_zone',
        'marketing_opt_in',
        'created_at',
    )
    list_select_related = ('user',)
    search_fields = ('user__email', 'first_name', 'last_name', 'phone')
    list_filter = ('marketing_opt_in', 'country_code')
