from django.contrib import admin

# Register your models here.
from main.models import Product, ProductImage

from simple_history.admin import SimpleHistoryAdmin


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    search_fields = ['code', 'name']
    list_filter = ('is_available', )

    list_display = [
        'name',
        'description',
        'code',
        'available_price',
        'old_price',
        'is_available',
    ]

    history_list_display = list_display
    inlines = [
        ProductImageInline
    ]
