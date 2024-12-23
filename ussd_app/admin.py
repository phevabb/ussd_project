from django.contrib import admin
from .models import ShoppingList,UserInfo

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("order_id", "phone_number", "list_name", "created_at", "status")
    list_editable = ("status",)

# Register your models here.
@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('phone_number','digital_address', 'area_name', 'payment_preference')