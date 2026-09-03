from django.contrib import admin

from .models import Category, Equipment, Location


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["asset_id", "name", "provider", "category", "location", "status"]
    list_filter = ["status", "category", "location"]
    search_fields = ["asset_id", "name", "model"]
