from django.contrib import admin

from .models import Artwork, ArtworkMovement, WarehouseActivity, WarehouseFollowUp, WarehouseStockItem


@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'inventory_number', 'author', 'storage_location', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'inventory_number', 'author', 'storage_location')


@admin.register(ArtworkMovement)
class ArtworkMovementAdmin(admin.ModelAdmin):
    list_display = ('artwork', 'movement_type', 'taken_by', 'movement_date', 'due_date', 'returned_at')
    list_filter = ('movement_type', 'movement_date', 'due_date', 'returned_at')
    search_fields = ('artwork__name', 'artwork__inventory_number', 'taken_by', 'phone_number')


@admin.register(WarehouseActivity)
class WarehouseActivityAdmin(admin.ModelAdmin):
    list_display = ('artwork', 'activity_date', 'activity_time', 'activity_type', 'status', 'responsible')
    list_filter = ('activity_type', 'status', 'activity_date')
    search_fields = ('artwork__name', 'responsible', 'notes')


@admin.register(WarehouseFollowUp)
class WarehouseFollowUpAdmin(admin.ModelAdmin):
    list_display = ('artwork', 'followup_date', 'responsible', 'status', 'destination')
    list_filter = ('status', 'followup_date')
    search_fields = ('artwork__name', 'responsible', 'reason', 'destination')


@admin.register(WarehouseStockItem)
class WarehouseStockItemAdmin(admin.ModelAdmin):
    list_display = ('material', 'batch', 'quantity', 'minimum_quantity', 'unit', 'expiry_date', 'location')
    list_filter = ('unit', 'expiry_date')
    search_fields = ('material', 'batch', 'item_class', 'location')
