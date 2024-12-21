from django.contrib import admin
from .models import ShoppingList

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("session_id", "phone_number", "list_name", "created_at")

# Register your models here.
