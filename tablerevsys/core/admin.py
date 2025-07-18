from django.contrib import admin
from .models import Branch, Table, Reservation
import datetime
from django import forms

# Register your models here.

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('code', 'branch', 'capacity')
    list_filter = ('branch', 'capacity')
    search_fields = ('code',)
    search_fields = ('code', 'branch__name')
    autocomplete_fields = ('branch',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'customer_name', 'branch', 'table',
        'date', 'time'
    )
    list_filter = ('branch', 'date')
    search_fields = (
        'customer_name', 'customer_email',
        'table__code', 'branch__name'
    )
    list_editable = ('branch', 'table', 'date', 'time')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Customer', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Reservation Details', {
            'fields': (('branch', 'table'), ('date', 'time'),
                       'adults', 'children', 'seniors', 'babies')
        }),
        ('Add-ons', {
            'fields': ('purpose', 'allergies', 'requests')
        }),
    )
    autocomplete_fields = ('branch', 'table')

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "time":
            choices = []
            start = datetime.time(11, 0)
            end = datetime.time(21, 30)
            current = start
            while current <= end:
                choices.append((current, current.strftime("%I:%M %p")))
                dt = datetime.datetime.combine(datetime.date.today(), current) + datetime.timedelta(minutes=15)
                current = dt.time()
            return forms.ChoiceField(choices=choices)
        return super().formfield_for_dbfield(db_field, request, **kwargs)